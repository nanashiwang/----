from __future__ import annotations

from dataclasses import dataclass
import importlib
import io
from contextlib import redirect_stderr, redirect_stdout
from typing import Any


@dataclass(slots=True)
class ModelBundle:
    model: Any
    model_name: str
    feature_columns: list[str]
    metrics: dict[str, float]
    experiment_mode: str
    taxonomy_feature_columns: list[str]
    baseline_mean: float = 0.0


class StubMeanModel:
    def __init__(self, baseline_mean: float):
        self.baseline_mean = baseline_mean

    def predict(self, rows: list[dict], feature_columns: list[str]) -> list[float]:
        predictions = []
        for row in rows:
            feature_sum = sum(float(row.get(column, 0.0) or 0.0) for column in feature_columns)
            predictions.append(self.baseline_mean + feature_sum / max(len(feature_columns), 1) * 0.01)
        return predictions


class ModelTrainer:
    def train(
        self,
        dataset: list[dict],
        feature_columns: list[str],
        label_column: str,
        model_name: str,
        cv_method: str,
        extra_params: dict[str, Any] | None = None,
        experiment_mode: str = 'baseline',
        taxonomy_feature_columns: list[str] | None = None,
    ) -> ModelBundle:
        extra_params = extra_params or {}
        taxonomy_feature_columns = taxonomy_feature_columns or []
        if not dataset or not feature_columns:
            raise ValueError('dataset is empty or feature columns are missing')

        labels = [float(row.get(label_column, 0.0) or 0.0) for row in dataset]
        baseline_mean = sum(labels) / len(labels)

        model = self._build_model(model_name, extra_params)
        if model is None:
            predictions = StubMeanModel(baseline_mean).predict(dataset, feature_columns)
            metrics = self._build_metrics(labels, predictions, cv_method, dataset, runtime_mode='stub')
            return ModelBundle(
                model=StubMeanModel(baseline_mean),
                model_name='stub_mean_model',
                feature_columns=feature_columns,
                metrics=metrics,
                experiment_mode=experiment_mode,
                taxonomy_feature_columns=taxonomy_feature_columns,
                baseline_mean=baseline_mean,
            )

        X = [[float(row.get(column, 0.0) or 0.0) for column in feature_columns] for row in dataset]
        y = labels
        model.fit(X, y)
        predictions = list(model.predict(X))
        metrics = self._build_metrics(y, predictions, cv_method, dataset, runtime_mode='model')
        return ModelBundle(
            model=model,
            model_name=model_name,
            feature_columns=feature_columns,
            metrics=metrics,
            experiment_mode=experiment_mode,
            taxonomy_feature_columns=taxonomy_feature_columns,
            baseline_mean=baseline_mean,
        )

    def _build_model(self, model_name: str, extra_params: dict[str, Any]):
        if model_name == 'xgboost_regressor':
            xgb_cls = self._optional_import('xgboost', 'XGBRegressor')
            if xgb_cls is not None:
                params = {'n_estimators': 60, 'max_depth': 3, 'learning_rate': 0.08, **extra_params}
                return xgb_cls(**params)
        rf_cls = self._optional_import('sklearn.ensemble', 'RandomForestRegressor')
        if rf_cls is not None:
            params = {'n_estimators': 100, 'random_state': 7, **extra_params}
            return rf_cls(**params)
        return None

    @staticmethod
    def _optional_import(module_name: str, attr_name: str):
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                module = importlib.import_module(module_name)
            return getattr(module, attr_name)
        except Exception:
            return None

    def _build_metrics(
        self,
        y_true: list[float],
        y_pred: list[float],
        cv_method: str,
        dataset: list[dict],
        *,
        runtime_mode: str,
    ) -> dict[str, float]:
        metrics = {
            'mae': self._mae(y_true, y_pred),
            'r2': self._r2(y_true, y_pred),
            'row_count': float(len(dataset)),
        }
        if cv_method == 'time_series_split' and len(dataset) >= 4:
            split_index = max(1, int(len(dataset) * 0.7))
            metrics['cv_mae'] = self._mae(y_true[split_index:], y_pred[split_index:])
        if runtime_mode == 'stub':
            metrics['runtime_mode'] = 0.0
        return metrics

    @staticmethod
    def _mae(y_true: list[float], y_pred: list[float]) -> float:
        if not y_true:
            return 0.0
        return sum(abs(a - b) for a, b in zip(y_true, y_pred)) / len(y_true)

    @staticmethod
    def _r2(y_true: list[float], y_pred: list[float]) -> float:
        if len(y_true) <= 1:
            return 0.0
        mean_value = sum(y_true) / len(y_true)
        total = sum((value - mean_value) ** 2 for value in y_true)
        residual = sum((a - b) ** 2 for a, b in zip(y_true, y_pred))
        return 0.0 if total == 0 else 1 - residual / total
