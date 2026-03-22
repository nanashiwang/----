from __future__ import annotations

from itertools import product
from math import sqrt
from typing import Any, Dict, Iterable, List

import pandas as pd

from backend.models.ml import MlExperimentRequest
from backend.services.settings_service import SettingsService
from src.data.db.sqlite_client import SQLiteClient
from src.ml.dataset_builder import DatasetBuilder
from src.ml.predictor import LinearFactorPredictor, SklearnModelPredictor
from src.ml.registry import (
    DEFAULT_FEATURE_COLUMNS,
    DEFAULT_LABEL_COLUMN,
    DEFAULT_SCORE_COLUMN,
    FEATURE_DESCRIPTIONS,
    FEATURE_LABELS,
    LABEL_DESCRIPTIONS,
    LABEL_LABELS,
    MODEL_DESCRIPTIONS,
    MODEL_LABELS,
    TUNING_DESCRIPTIONS,
    TUNING_LABELS,
)
from src.ml.selector import FeatureSelector
from src.ml.trainer import (
    LinearFactorTrainer,
    SklearnRandomForestTrainer,
    SklearnRidgeTrainer,
    sklearn_runtime_available,
    sklearn_runtime_error_message,
)

_OPTUNA_IMPORT_ERROR = None
try:
    import optuna
except Exception as exc:  # pragma: no cover - 由运行环境决定
    optuna = None
    _OPTUNA_IMPORT_ERROR = exc


def optuna_runtime_available() -> bool:
    return optuna is not None


def optuna_runtime_error_message() -> str:
    if _OPTUNA_IMPORT_ERROR is None:
        return ""
    return str(_OPTUNA_IMPORT_ERROR)


class MLExperimentService:
    def __init__(self, db: SQLiteClient):
        self.db = db
        self.settings = SettingsService(db)
        self.dataset_builder = DatasetBuilder(db)
        self.selector = FeatureSelector()
        self.linear_trainer = LinearFactorTrainer()
        self.linear_predictor = LinearFactorPredictor()
        self.ridge_trainer = SklearnRidgeTrainer()
        self.random_forest_trainer = SklearnRandomForestTrainer()
        self.sklearn_predictor = SklearnModelPredictor()

    def get_options(self) -> Dict[str, Any]:
        date_bounds = self._get_date_bounds()
        symbols = self._list_symbols()
        default_symbols = self._get_default_symbols()
        defaults = self._build_defaults(date_bounds, default_symbols)
        sklearn_available = sklearn_runtime_available()
        optuna_available = optuna_runtime_available()

        return {
            "cycle": "daily",
            "cycle_label": "日线同周期",
            "date_bounds": date_bounds,
            "symbols": symbols,
            "feature_options": [
                {
                    "value": feature,
                    "label": FEATURE_LABELS.get(feature, feature),
                    "description": FEATURE_DESCRIPTIONS.get(feature, ""),
                }
                for feature in DEFAULT_FEATURE_COLUMNS
            ],
            "label_options": [
                {
                    "value": label,
                    "label": LABEL_LABELS.get(label, label),
                    "description": LABEL_DESCRIPTIONS.get(label, ""),
                }
                for label in ("future_return", "future_excess_return", "future_benchmark_excess_return")
            ],
            "model_options": [
                {
                    "value": "linear_factor",
                    "label": MODEL_LABELS["linear_factor"],
                    "description": MODEL_DESCRIPTIONS["linear_factor"],
                    "meta": {"supports_tuning": False, "requires_sklearn": False},
                },
                {
                    "value": "sklearn_ridge",
                    "label": MODEL_LABELS["sklearn_ridge"],
                    "description": MODEL_DESCRIPTIONS["sklearn_ridge"],
                    "disabled": not sklearn_available,
                    "meta": {"supports_tuning": True, "requires_sklearn": True},
                },
                {
                    "value": "sklearn_random_forest",
                    "label": MODEL_LABELS["sklearn_random_forest"],
                    "description": MODEL_DESCRIPTIONS["sklearn_random_forest"],
                    "disabled": not sklearn_available,
                    "meta": {"supports_tuning": True, "requires_sklearn": True},
                },
            ],
            "tuning_options": [
                {
                    "value": "none",
                    "label": TUNING_LABELS["none"],
                    "description": TUNING_DESCRIPTIONS["none"],
                },
                {
                    "value": "grid_search",
                    "label": TUNING_LABELS["grid_search"],
                    "description": TUNING_DESCRIPTIONS["grid_search"],
                    "disabled": not sklearn_available,
                },
                {
                    "value": "optuna",
                    "label": TUNING_LABELS["optuna"],
                    "description": TUNING_DESCRIPTIONS["optuna"],
                    "disabled": not sklearn_available or not optuna_available,
                },
            ],
            "defaults": defaults,
            "runtime": {
                "sklearn_available": sklearn_available,
                "sklearn_error": "" if sklearn_available else sklearn_runtime_error_message(),
                "optuna_available": optuna_available,
                "optuna_error": "" if optuna_available else optuna_runtime_error_message(),
            },
        }

    def run_experiment(self, payload: MlExperimentRequest) -> Dict[str, Any]:
        symbol_list = self._resolve_symbols(
            payload.symbols,
            payload.train_start_date,
            payload.predict_end_date,
        )
        if not symbol_list:
            raise ValueError("当前时间范围内没有可用股票样本，请先同步行情数据")

        query_end = (
            pd.Timestamp(payload.predict_end_date) + pd.Timedelta(days=max(payload.hold_days * 3, 15))
        ).strftime("%Y-%m-%d")
        dataset = self.dataset_builder.build_dataset(
            symbols=symbol_list,
            query_start_date=payload.train_start_date,
            query_end_date=query_end,
            signal_start_date=payload.train_start_date,
            signal_end_date=payload.predict_end_date,
            hold_days=payload.hold_days,
        )
        if dataset.empty:
            raise ValueError("当前条件下未构建出可训练样本，请先补齐历史行情和扩展指标数据")

        label_col = payload.label_column or DEFAULT_LABEL_COLUMN
        candidate_features = [
            feature for feature in (payload.feature_columns or DEFAULT_FEATURE_COLUMNS) if feature in dataset.columns
        ]
        if not candidate_features:
            raise ValueError("当前样本中没有可用自变量，请重新选择特征列")

        training_df = dataset[
            (dataset["trade_date"] >= pd.Timestamp(payload.train_start_date))
            & (dataset["trade_date"] <= pd.Timestamp(payload.train_end_date))
            & dataset["sell_date"].notna()
            & (dataset["sell_date"] < pd.Timestamp(payload.predict_start_date))
        ].copy()
        prediction_df = dataset[
            (dataset["trade_date"] >= pd.Timestamp(payload.predict_start_date))
            & (dataset["trade_date"] <= pd.Timestamp(payload.predict_end_date))
            & dataset["buy_date"].notna()
        ].copy()

        if training_df.empty:
            raise ValueError("训练窗口内没有足够样本，请扩大训练日期范围")
        if prediction_df.empty:
            raise ValueError("预测窗口内没有可用样本，请检查日期范围和股票池")

        selection = self._select_features(
            training_df=training_df,
            candidate_features=candidate_features,
            label_col=label_col,
            use_feature_selection=payload.use_feature_selection,
            max_features=payload.max_features,
        )
        selected_features = selection["selected_features"]
        if not selected_features:
            raise ValueError("没有筛选出可用特征，请放宽窗口或减少过滤强度")

        fit_df, validation_df = self._split_training_validation(training_df)
        tuning_summary = self._resolve_tuning(
            model_type=payload.model_type,
            tuning_method=payload.tuning_method,
            fit_df=fit_df,
            validation_df=validation_df,
            selected_features=selected_features,
            label_col=label_col,
            feature_stats=selection["feature_stats"],
            tuning_trials=payload.tuning_trials,
        )
        best_params = tuning_summary.get("best_params", {})

        model = self._fit_model(
            model_type=payload.model_type,
            dataset=training_df,
            selected_features=selected_features,
            label_col=label_col,
            feature_stats=selection["feature_stats"],
            params=best_params,
        )

        training_scored = self._predict_scores(payload.model_type, training_df, model)
        prediction_scored = self._predict_scores(payload.model_type, prediction_df, model)
        train_metrics = self._evaluate_scored_frame(training_scored, label_col)
        predictions = self._build_prediction_rows(
            scored_frame=prediction_scored,
            label_col=label_col,
            prediction_top_n=payload.prediction_top_n,
        )

        return {
            "cycle": "daily",
            "params": {
                **payload.model_dump(),
                "resolved_symbols": symbol_list,
            },
            "sample_summary": {
                "symbol_count": len(symbol_list),
                "candidate_feature_count": len(candidate_features),
                "selected_feature_count": len(selected_features),
                "train_samples": int(len(training_df)),
                "validation_samples": int(len(validation_df)),
                "prediction_samples": int(len(prediction_df)),
                "prediction_output_rows": len(predictions),
            },
            "selected_features": selected_features,
            "feature_stats": selection["feature_stats"],
            "model_weights": self._build_model_weights(model),
            "training_summary": {
                "train_start_date": training_df["trade_date"].min().strftime("%Y-%m-%d"),
                "train_end_date": training_df["trade_date"].max().strftime("%Y-%m-%d"),
                "predict_start_date": prediction_df["trade_date"].min().strftime("%Y-%m-%d"),
                "predict_end_date": prediction_df["trade_date"].max().strftime("%Y-%m-%d"),
                "train_samples": int(len(training_df)),
                "validation_samples": int(len(validation_df)),
                "prediction_samples": int(len(prediction_df)),
                "train_score": self._to_number(model.get("train_score")),
                "train_metrics": train_metrics,
                "validation_metrics": tuning_summary.get("validation_metrics", {}),
            },
            "tuning_summary": tuning_summary,
            "prediction_summary": self._build_prediction_summary(predictions, label_col),
            "predictions": predictions,
        }

    def _get_date_bounds(self) -> Dict[str, str]:
        sql = """
            SELECT MIN(trade_date) AS min_date, MAX(trade_date) AS max_date
            FROM stock_data
        """
        with self.db.get_connection() as conn:
            row = conn.execute(sql).fetchone()
        if not row or not row["min_date"] or not row["max_date"]:
            return {"min_date": "", "max_date": ""}
        return {"min_date": str(row["min_date"]), "max_date": str(row["max_date"])}

    def _list_symbols(self) -> List[str]:
        sql = """
            SELECT DISTINCT ts_code
            FROM stock_data
            ORDER BY ts_code
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(sql).fetchall()
        return [str(row["ts_code"]).upper() for row in rows if row["ts_code"]]

    def _get_default_symbols(self) -> List[str]:
        raw_symbols = self.settings.get_raw_value("market_data", "symbols") or ""
        symbols = []
        for value in str(raw_symbols).replace("\n", ",").split(","):
            symbol = value.strip().upper()
            if symbol:
                symbols.append(symbol)
        return list(dict.fromkeys(symbols))

    def _build_defaults(self, date_bounds: Dict[str, str], default_symbols: List[str]) -> Dict[str, Any]:
        min_date = date_bounds.get("min_date") or ""
        max_date = date_bounds.get("max_date") or ""
        if not min_date or not max_date:
            return {
                "symbols": default_symbols,
                "feature_columns": list(DEFAULT_FEATURE_COLUMNS),
                "label_column": DEFAULT_LABEL_COLUMN,
                "model_type": "linear_factor",
                "tuning_method": "none",
                "train_start_date": "",
                "train_end_date": "",
                "predict_start_date": "",
                "predict_end_date": "",
                "hold_days": 5,
                "use_feature_selection": True,
                "max_features": 8,
                "prediction_top_n": 20,
                "tuning_trials": 20,
            }

        min_dt = pd.Timestamp(min_date)
        max_dt = pd.Timestamp(max_date)
        total_days = max((max_dt - min_dt).days, 1)
        if total_days < 2:
            return {
                "symbols": default_symbols,
                "feature_columns": list(DEFAULT_FEATURE_COLUMNS),
                "label_column": DEFAULT_LABEL_COLUMN,
                "model_type": "linear_factor",
                "tuning_method": "none",
                "train_start_date": "",
                "train_end_date": "",
                "predict_start_date": "",
                "predict_end_date": "",
                "hold_days": 5,
                "use_feature_selection": True,
                "max_features": 8,
                "prediction_top_n": 20,
                "tuning_trials": 20,
            }

        if total_days >= 60:
            predict_end = max_dt
            predict_start = max(max_dt - pd.Timedelta(days=20), min_dt)
            train_end = max(predict_start - pd.Timedelta(days=1), min_dt)
            train_start = max(train_end - pd.Timedelta(days=180), min_dt)
        else:
            midpoint = min_dt + pd.Timedelta(days=max(total_days // 2, 1))
            train_start = min_dt
            train_end = min(midpoint, max_dt)
            predict_start = min(train_end + pd.Timedelta(days=1), max_dt)
            predict_end = max_dt

        if train_end >= predict_start:
            return {
                "symbols": default_symbols,
                "feature_columns": list(DEFAULT_FEATURE_COLUMNS),
                "label_column": DEFAULT_LABEL_COLUMN,
                "model_type": "linear_factor",
                "tuning_method": "none",
                "train_start_date": "",
                "train_end_date": "",
                "predict_start_date": "",
                "predict_end_date": "",
                "hold_days": 5,
                "use_feature_selection": True,
                "max_features": 8,
                "prediction_top_n": 20,
                "tuning_trials": 20,
            }

        return {
            "symbols": default_symbols,
            "feature_columns": list(DEFAULT_FEATURE_COLUMNS),
            "label_column": DEFAULT_LABEL_COLUMN,
            "model_type": "linear_factor",
            "tuning_method": "none",
            "train_start_date": train_start.strftime("%Y-%m-%d"),
            "train_end_date": train_end.strftime("%Y-%m-%d"),
            "predict_start_date": predict_start.strftime("%Y-%m-%d"),
            "predict_end_date": predict_end.strftime("%Y-%m-%d"),
            "hold_days": 5,
            "use_feature_selection": True,
            "max_features": 8,
            "prediction_top_n": 20,
            "tuning_trials": 20,
        }

    def _resolve_symbols(
        self,
        symbols: Iterable[str],
        start_date: str,
        end_date: str,
    ) -> List[str]:
        resolved = [str(item).strip().upper() for item in symbols if str(item).strip()]
        if resolved:
            return list(dict.fromkeys(resolved))

        sql = """
            SELECT DISTINCT ts_code
            FROM stock_data
            WHERE trade_date BETWEEN ? AND ?
            ORDER BY ts_code
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(sql, (start_date, end_date)).fetchall()
        return [str(row["ts_code"]).upper() for row in rows if row["ts_code"]]

    def _select_features(
        self,
        *,
        training_df: pd.DataFrame,
        candidate_features: List[str],
        label_col: str,
        use_feature_selection: bool,
        max_features: int,
    ) -> Dict[str, Any]:
        selection = self.selector.select(
            training_df,
            candidate_features=candidate_features,
            label_col=label_col,
            top_k=max(max_features, 1),
        )
        if use_feature_selection:
            return selection

        manual_features = [feature for feature in candidate_features if feature in training_df.columns]
        return {
            "selected_features": manual_features,
            "feature_stats": selection["feature_stats"],
            "label_col": label_col,
        }

    def _split_training_validation(self, training_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        unique_dates = sorted(training_df["trade_date"].dropna().unique().tolist())
        if len(unique_dates) < 8:
            return training_df.copy(), training_df.iloc[0:0].copy()

        validation_days = max(3, int(len(unique_dates) * 0.2))
        validation_start = unique_dates[-validation_days]
        fit_df = training_df[training_df["trade_date"] < validation_start].copy()
        validation_df = training_df[training_df["trade_date"] >= validation_start].copy()
        if fit_df.empty or validation_df.empty:
            return training_df.copy(), training_df.iloc[0:0].copy()
        return fit_df, validation_df

    def _resolve_tuning(
        self,
        *,
        model_type: str,
        tuning_method: str,
        fit_df: pd.DataFrame,
        validation_df: pd.DataFrame,
        selected_features: List[str],
        label_col: str,
        feature_stats: List[Dict[str, Any]],
        tuning_trials: int,
    ) -> Dict[str, Any]:
        default_params = self._default_model_params(model_type)
        base_summary = {
            "method": tuning_method,
            "best_params": default_params,
            "validation_metrics": {},
            "history": [],
            "status": "skipped",
            "message": "",
        }

        if model_type == "linear_factor":
            metrics = self._evaluate_candidate(
                model_type=model_type,
                fit_df=fit_df,
                validation_df=validation_df,
                selected_features=selected_features,
                label_col=label_col,
                feature_stats=feature_stats,
                params=default_params,
            )
            base_summary["validation_metrics"] = metrics
            base_summary["message"] = "线性因子模型没有可调超参数，已直接使用默认逻辑。"
            return base_summary

        if tuning_method == "optuna" and not optuna_runtime_available():
            raise ValueError("当前环境未安装 optuna，暂时无法使用 Optuna 调优")

        if validation_df.empty:
            base_summary["message"] = "训练样本不足，无法切出验证集，已跳过调优。"
            return base_summary

        if tuning_method == "none":
            metrics = self._evaluate_candidate(
                model_type=model_type,
                fit_df=fit_df,
                validation_df=validation_df,
                selected_features=selected_features,
                label_col=label_col,
                feature_stats=feature_stats,
                params=default_params,
            )
            return {
                **base_summary,
                "method": "none",
                "status": "completed",
                "message": "已使用默认参数完成训练。",
                "validation_metrics": metrics,
                "history": [{"params": default_params, "metrics": metrics}],
            }

        if tuning_method == "grid_search":
            return self._grid_search(
                model_type=model_type,
                fit_df=fit_df,
                validation_df=validation_df,
                selected_features=selected_features,
                label_col=label_col,
                feature_stats=feature_stats,
            )

        if tuning_method == "optuna":
            return self._optuna_search(
                model_type=model_type,
                fit_df=fit_df,
                validation_df=validation_df,
                selected_features=selected_features,
                label_col=label_col,
                feature_stats=feature_stats,
                tuning_trials=tuning_trials,
            )

        return base_summary

    def _grid_search(
        self,
        *,
        model_type: str,
        fit_df: pd.DataFrame,
        validation_df: pd.DataFrame,
        selected_features: List[str],
        label_col: str,
        feature_stats: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        history = []
        best_score = float("-inf")
        best_params = self._default_model_params(model_type)
        best_metrics = {}

        for params in self._grid_candidates(model_type):
            metrics = self._evaluate_candidate(
                model_type=model_type,
                fit_df=fit_df,
                validation_df=validation_df,
                selected_features=selected_features,
                label_col=label_col,
                feature_stats=feature_stats,
                params=params,
            )
            score = self._score_metrics(metrics)
            history.append({"params": params, "metrics": metrics, "score": self._to_number(score)})
            if score > best_score:
                best_score = score
                best_params = params
                best_metrics = metrics

        history = sorted(history, key=lambda item: item["score"], reverse=True)
        return {
            "method": "grid_search",
            "status": "completed",
            "message": f"已完成 {len(history)} 组参数网格搜索。",
            "best_params": best_params,
            "validation_metrics": best_metrics,
            "history": history[:10],
        }

    def _optuna_search(
        self,
        *,
        model_type: str,
        fit_df: pd.DataFrame,
        validation_df: pd.DataFrame,
        selected_features: List[str],
        label_col: str,
        feature_stats: List[Dict[str, Any]],
        tuning_trials: int,
    ) -> Dict[str, Any]:
        history: List[Dict[str, Any]] = []

        def objective(trial):
            params = self._optuna_params(model_type, trial)
            metrics = self._evaluate_candidate(
                model_type=model_type,
                fit_df=fit_df,
                validation_df=validation_df,
                selected_features=selected_features,
                label_col=label_col,
                feature_stats=feature_stats,
                params=params,
            )
            score = self._score_metrics(metrics)
            history.append(
                {
                    "params": params,
                    "metrics": metrics,
                    "score": self._to_number(score),
                }
            )
            return score

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=tuning_trials)
        best_params = self._normalize_best_params(model_type, study.best_params)
        best_metrics = next((item["metrics"] for item in history if item["params"] == best_params), {})
        history = sorted(history, key=lambda item: item["score"], reverse=True)
        return {
            "method": "optuna",
            "status": "completed",
            "message": f"已完成 {len(history)} 次 Optuna 调优。",
            "best_params": best_params,
            "validation_metrics": best_metrics,
            "history": history[:10],
        }

    def _default_model_params(self, model_type: str) -> Dict[str, Any]:
        if model_type == "linear_factor":
            return {}
        if model_type == "sklearn_ridge":
            return {"alpha": 1.0}
        if model_type == "sklearn_random_forest":
            return {
                "n_estimators": 200,
                "max_depth": 6,
                "min_samples_leaf": 2,
                "min_samples_split": 4,
                "max_features": "sqrt",
            }
        raise ValueError(f"暂不支持的模型类型: {model_type}")

    def _grid_candidates(self, model_type: str) -> List[Dict[str, Any]]:
        if model_type == "sklearn_ridge":
            return [{"alpha": alpha} for alpha in (0.1, 0.3, 1.0, 3.0, 10.0)]
        if model_type == "sklearn_random_forest":
            candidates = []
            for n_estimators, max_depth, min_samples_leaf in product(
                (100, 200),
                (4, 6, 8, None),
                (1, 2),
            ):
                candidates.append(
                    {
                        "n_estimators": n_estimators,
                        "max_depth": max_depth,
                        "min_samples_leaf": min_samples_leaf,
                        "min_samples_split": 4,
                        "max_features": "sqrt",
                    }
                )
            return candidates
        return [self._default_model_params(model_type)]

    def _optuna_params(self, model_type: str, trial) -> Dict[str, Any]:
        if model_type == "sklearn_ridge":
            return {"alpha": float(trial.suggest_float("alpha", 0.05, 20.0, log=True))}
        if model_type == "sklearn_random_forest":
            return {
                "n_estimators": int(trial.suggest_int("n_estimators", 80, 320, step=40)),
                "max_depth": trial.suggest_categorical("max_depth", [None, 4, 6, 8, 10, 12]),
                "min_samples_leaf": int(trial.suggest_int("min_samples_leaf", 1, 6)),
                "min_samples_split": int(trial.suggest_int("min_samples_split", 2, 12)),
                "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2", None]),
            }
        return self._default_model_params(model_type)

    def _normalize_best_params(self, model_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(params)
        if model_type == "sklearn_ridge" and "alpha" in normalized:
            normalized["alpha"] = float(normalized["alpha"])
        if model_type == "sklearn_random_forest":
            for key in ("n_estimators", "min_samples_leaf", "min_samples_split"):
                if key in normalized and normalized[key] is not None:
                    normalized[key] = int(normalized[key])
        return normalized

    def _evaluate_candidate(
        self,
        *,
        model_type: str,
        fit_df: pd.DataFrame,
        validation_df: pd.DataFrame,
        selected_features: List[str],
        label_col: str,
        feature_stats: List[Dict[str, Any]],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        if validation_df.empty:
            return {}
        model = self._fit_model(
            model_type=model_type,
            dataset=fit_df,
            selected_features=selected_features,
            label_col=label_col,
            feature_stats=feature_stats,
            params=params,
        )
        scored = self._predict_scores(model_type, validation_df, model)
        return self._evaluate_scored_frame(scored, label_col)

    def _fit_model(
        self,
        *,
        model_type: str,
        dataset: pd.DataFrame,
        selected_features: List[str],
        label_col: str,
        feature_stats: List[Dict[str, Any]],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        if model_type == "linear_factor":
            return self.linear_trainer.fit(
                dataset,
                selected_features,
                label_col=label_col,
                feature_stats=feature_stats,
            )
        if model_type == "sklearn_ridge":
            return self.ridge_trainer.fit(
                dataset,
                selected_features,
                label_col=label_col,
                alpha=float(params.get("alpha", 1.0)),
            )
        if model_type == "sklearn_random_forest":
            return self.random_forest_trainer.fit(
                dataset,
                selected_features,
                label_col=label_col,
                n_estimators=int(params.get("n_estimators", 200)),
                max_depth=params.get("max_depth"),
                min_samples_leaf=int(params.get("min_samples_leaf", 2)),
                min_samples_split=int(params.get("min_samples_split", 4)),
                max_features=params.get("max_features", "sqrt"),
            )
        raise ValueError(f"暂不支持的模型类型: {model_type}")

    def _predict_scores(self, model_type: str, dataset: pd.DataFrame, model: Dict[str, Any]) -> pd.DataFrame:
        if model_type == "linear_factor":
            return self.linear_predictor.predict(dataset, model, score_col=DEFAULT_SCORE_COLUMN)
        if model_type in {"sklearn_ridge", "sklearn_random_forest"}:
            return self.sklearn_predictor.predict(dataset, model, score_col=DEFAULT_SCORE_COLUMN)
        raise ValueError(f"暂不支持的模型类型: {model_type}")

    def _evaluate_scored_frame(self, frame: pd.DataFrame, label_col: str) -> Dict[str, Any]:
        if frame.empty or label_col not in frame.columns or DEFAULT_SCORE_COLUMN not in frame.columns:
            return {}

        valid = frame[[DEFAULT_SCORE_COLUMN, label_col]].dropna().copy()
        if valid.empty:
            return {
                "sample_count": 0,
                "rank_ic": 0.0,
                "ic": 0.0,
                "rmse": 0.0,
                "mae": 0.0,
                "directional_accuracy": 0.0,
            }

        score_series = pd.to_numeric(valid[DEFAULT_SCORE_COLUMN], errors="coerce")
        label_series = pd.to_numeric(valid[label_col], errors="coerce")
        valid_mask = score_series.notna() & label_series.notna()
        score_series = score_series.loc[valid_mask]
        label_series = label_series.loc[valid_mask]
        if score_series.empty:
            return {
                "sample_count": 0,
                "rank_ic": 0.0,
                "ic": 0.0,
                "rmse": 0.0,
                "mae": 0.0,
                "directional_accuracy": 0.0,
            }

        rank_ic = score_series.rank().corr(label_series.rank())
        ic = score_series.corr(label_series)
        delta = score_series - label_series
        directional = (score_series >= 0).eq(label_series >= 0).mean()
        return {
            "sample_count": int(len(score_series)),
            "rank_ic": self._to_number(rank_ic),
            "ic": self._to_number(ic),
            "rmse": self._to_number(sqrt(float((delta.pow(2)).mean()))),
            "mae": self._to_number(float(delta.abs().mean())),
            "directional_accuracy": self._to_number(float(directional)),
        }

    def _score_metrics(self, metrics: Dict[str, Any]) -> float:
        if not metrics or metrics.get("sample_count", 0) <= 0:
            return float("-inf")
        return float(metrics.get("rank_ic", 0.0))

    def _build_model_weights(self, model: Dict[str, Any]) -> List[Dict[str, Any]]:
        weights = model.get("weights", {})
        if not isinstance(weights, dict):
            return []
        ranked = sorted(weights.items(), key=lambda item: abs(item[1]), reverse=True)
        return [
            {
                "feature": feature,
                "feature_label": FEATURE_LABELS.get(feature, feature),
                "weight": self._to_number(weight),
            }
            for feature, weight in ranked
        ]

    def _build_prediction_rows(
        self,
        *,
        scored_frame: pd.DataFrame,
        label_col: str,
        prediction_top_n: int,
    ) -> List[Dict[str, Any]]:
        if scored_frame.empty:
            return []

        ranked = scored_frame.sort_values(
            ["trade_date", DEFAULT_SCORE_COLUMN],
            ascending=[True, False],
        ).copy()
        ranked["daily_rank"] = ranked.groupby("trade_date").cumcount() + 1
        ranked = ranked[ranked["daily_rank"] <= prediction_top_n].copy()

        rows = []
        for row in ranked.to_dict("records"):
            rows.append(
                {
                    "trade_date": pd.Timestamp(row["trade_date"]).strftime("%Y-%m-%d"),
                    "ts_code": row["ts_code"],
                    "prediction_score": self._to_number(row.get(DEFAULT_SCORE_COLUMN)),
                    "daily_rank": int(row.get("daily_rank") or 0),
                    "buy_date": self._format_date(row.get("buy_date")),
                    "sell_date": self._format_date(row.get("sell_date")),
                    "actual_label": self._to_number(row.get(label_col)),
                    "future_return": self._to_number(row.get("future_return")),
                    "future_excess_return": self._to_number(row.get("future_excess_return")),
                }
            )

        return rows

    def _build_prediction_summary(
        self,
        predictions: List[Dict[str, Any]],
        label_col: str,
    ) -> Dict[str, Any]:
        if not predictions:
            return {
                "row_count": 0,
                "label_column": label_col,
                "avg_prediction_score": 0.0,
                "avg_actual_label": 0.0,
                "avg_future_return": 0.0,
                "positive_future_return_ratio": 0.0,
            }

        frame = pd.DataFrame(predictions)
        actual_label_series = pd.to_numeric(frame["actual_label"], errors="coerce")
        future_return_series = pd.to_numeric(frame["future_return"], errors="coerce")
        prediction_series = pd.to_numeric(frame["prediction_score"], errors="coerce")

        return {
            "row_count": int(len(frame)),
            "label_column": label_col,
            "avg_prediction_score": self._to_number(prediction_series.mean()),
            "avg_actual_label": self._to_number(actual_label_series.mean()),
            "avg_future_return": self._to_number(future_return_series.mean()),
            "positive_future_return_ratio": self._to_number((future_return_series > 0).mean()),
        }

    def _format_date(self, value: Any) -> str:
        if value in (None, "", pd.NaT):
            return ""
        return pd.Timestamp(value).strftime("%Y-%m-%d")

    def _to_number(self, value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            if pd.isna(value):
                return 0.0
            return float(value)
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return 0.0
        if pd.isna(parsed):
            return 0.0
        return parsed
