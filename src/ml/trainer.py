from typing import Dict, Iterable, Optional

import pandas as pd

from .registry import DEFAULT_LABEL_COLUMN

_SKLEARN_IMPORT_ERROR = None
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
except Exception as exc:  # pragma: no cover - 由运行环境决定
    Pipeline = None
    SimpleImputer = None
    StandardScaler = None
    Ridge = None
    RandomForestRegressor = None
    _SKLEARN_IMPORT_ERROR = exc


def sklearn_runtime_available() -> bool:
    return (
        Pipeline is not None
        and SimpleImputer is not None
        and StandardScaler is not None
        and Ridge is not None
        and RandomForestRegressor is not None
    )


def sklearn_runtime_error_message() -> str:
    if _SKLEARN_IMPORT_ERROR is None:
        return ""
    return str(_SKLEARN_IMPORT_ERROR)


def _build_runtime_error() -> ValueError:
    detail = sklearn_runtime_error_message()
    suffix = f"（当前环境错误：{detail}）" if detail else ""
    return ValueError(
        f"请先安装兼容版本的 scikit-learn / scipy / numpy 后再运行 sklearn 模型{suffix}"
    )


def _prepare_training_frame(
    dataset: pd.DataFrame,
    features: Iterable[str],
    label_col: str,
) -> tuple[list[str], pd.DataFrame, pd.Series]:
    feature_list = [item for item in features if item in dataset.columns]
    if not feature_list:
        raise ValueError("训练失败：没有可用特征")

    working = dataset.dropna(subset=[label_col]).copy()
    if working.empty:
        raise ValueError("训练失败：训练集标签为空")

    train_x = working[feature_list].apply(pd.to_numeric, errors="coerce")
    train_y = pd.to_numeric(working[label_col], errors="coerce")
    valid_mask = train_y.notna()
    train_x = train_x.loc[valid_mask].copy()
    train_y = train_y.loc[valid_mask].copy()
    if train_x.empty or train_y.empty:
        raise ValueError("训练失败：训练集标签为空")
    return feature_list, train_x, train_y


class LinearFactorTrainer:
    """第一版训练器：用训练窗口中的 IC 构造线性因子权重。"""

    def fit(
        self,
        dataset: pd.DataFrame,
        features: Iterable[str],
        label_col: str = DEFAULT_LABEL_COLUMN,
        feature_stats: Optional[Iterable[Dict]] = None,
    ) -> Dict:
        feature_list = [item for item in features if item in dataset.columns]
        if not feature_list:
            raise ValueError("训练失败：没有可用特征")

        working = dataset.dropna(subset=[label_col]).copy()
        if working.empty:
            raise ValueError("训练失败：训练集标签为空")

        means = {}
        stds = {}
        weights = {}
        stat_map = {item["feature"]: item for item in (feature_stats or [])}

        for feature in feature_list:
            series = pd.to_numeric(working[feature], errors="coerce")
            mean_value = float(series.mean()) if pd.notna(series.mean()) else 0.0
            std_value = float(series.std(ddof=0)) if pd.notna(series.std(ddof=0)) else 0.0
            means[feature] = mean_value
            stds[feature] = std_value if std_value > 1e-8 else 1.0

            stat = stat_map.get(feature)
            if stat:
                weights[feature] = float(stat.get("ic", 0.0))
            else:
                valid = working[[feature, label_col]].dropna()
                corr = valid[feature].corr(valid[label_col]) if len(valid) > 1 else 0.0
                weights[feature] = float(corr) if pd.notna(corr) else 0.0

        total_abs_weight = sum(abs(value) for value in weights.values())
        if total_abs_weight <= 1e-8:
            equal_weight = 1.0 / len(feature_list)
            weights = {feature: equal_weight for feature in feature_list}
        else:
            weights = {feature: value / total_abs_weight for feature, value in weights.items()}

        return {
            "model_type": "linear_factor",
            "label_col": label_col,
            "features": feature_list,
            "weights": weights,
            "means": means,
            "stds": stds,
            "train_samples": int(len(working)),
        }


class SklearnRidgeTrainer:
    """scikit-learn 基线：StandardScaler + Ridge 回归。"""

    def fit(
        self,
        dataset: pd.DataFrame,
        features: Iterable[str],
        label_col: str = DEFAULT_LABEL_COLUMN,
        alpha: float = 1.0,
    ) -> Dict:
        if not sklearn_runtime_available():
            raise _build_runtime_error()

        feature_list, train_x, train_y = _prepare_training_frame(dataset, features, label_col)
        pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", Ridge(alpha=alpha)),
            ]
        )
        pipeline.fit(train_x, train_y)

        estimator = pipeline.named_steps["model"]
        coefficients = {
            feature: float(weight)
            for feature, weight in zip(feature_list, estimator.coef_, strict=False)
        }
        return {
            "model_type": "sklearn_ridge",
            "label_col": label_col,
            "features": feature_list,
            "pipeline": pipeline,
            "weights": coefficients,
            "intercept": float(estimator.intercept_),
            "alpha": float(alpha),
            "train_samples": int(len(train_y)),
            "train_score": float(pipeline.score(train_x, train_y)),
        }


class SklearnRandomForestTrainer:
    """scikit-learn 随机森林回归器。"""

    def fit(
        self,
        dataset: pd.DataFrame,
        features: Iterable[str],
        label_col: str = DEFAULT_LABEL_COLUMN,
        n_estimators: int = 200,
        max_depth: Optional[int] = 6,
        min_samples_leaf: int = 2,
        min_samples_split: int = 4,
        max_features: str | int | float | None = "sqrt",
        random_state: int = 42,
    ) -> Dict:
        if not sklearn_runtime_available():
            raise _build_runtime_error()

        feature_list, train_x, train_y = _prepare_training_frame(dataset, features, label_col)
        pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=n_estimators,
                        max_depth=max_depth,
                        min_samples_leaf=min_samples_leaf,
                        min_samples_split=min_samples_split,
                        max_features=max_features,
                        random_state=random_state,
                        n_jobs=1,
                    ),
                ),
            ]
        )
        pipeline.fit(train_x, train_y)

        estimator = pipeline.named_steps["model"]
        weights = {
            feature: float(weight)
            for feature, weight in zip(feature_list, estimator.feature_importances_, strict=False)
        }
        return {
            "model_type": "sklearn_random_forest",
            "label_col": label_col,
            "features": feature_list,
            "pipeline": pipeline,
            "weights": weights,
            "n_estimators": int(n_estimators),
            "max_depth": None if max_depth is None else int(max_depth),
            "min_samples_leaf": int(min_samples_leaf),
            "min_samples_split": int(min_samples_split),
            "max_features": max_features,
            "train_samples": int(len(train_y)),
            "train_score": float(pipeline.score(train_x, train_y)),
        }
