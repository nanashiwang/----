from typing import Dict, Iterable, Optional

import pandas as pd

from .registry import DEFAULT_LABEL_COLUMN

_SKLEARN_IMPORT_ERROR = None
try:
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
except Exception as exc:  # pragma: no cover - 由运行环境决定
    Pipeline = None
    SimpleImputer = None
    StandardScaler = None
    Ridge = None
    _SKLEARN_IMPORT_ERROR = exc


def sklearn_runtime_available() -> bool:
    return Pipeline is not None and SimpleImputer is not None and StandardScaler is not None and Ridge is not None


def sklearn_runtime_error_message() -> str:
    if _SKLEARN_IMPORT_ERROR is None:
        return ""
    return str(_SKLEARN_IMPORT_ERROR)


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
            detail = sklearn_runtime_error_message()
            suffix = f"（当前环境错误：{detail}）" if detail else ""
            raise ValueError(f"请先安装兼容版本的 scikit-learn / scipy / numpy 后再运行 sklearn 基线模型{suffix}")

        feature_list = [item for item in features if item in dataset.columns]
        if not feature_list:
            raise ValueError("训练失败：没有可用特征")

        working = dataset.dropna(subset=[label_col]).copy()
        if working.empty:
            raise ValueError("训练失败：训练集标签为空")

        train_x = working[feature_list].apply(pd.to_numeric, errors="coerce")
        train_y = pd.to_numeric(working[label_col], errors="coerce")

        pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("ridge", Ridge(alpha=alpha)),
            ]
        )
        pipeline.fit(train_x, train_y)

        ridge = pipeline.named_steps["ridge"]
        coefficients = {
            feature: float(weight)
            for feature, weight in zip(feature_list, ridge.coef_, strict=False)
        }
        return {
            "model_type": "sklearn_ridge",
            "label_col": label_col,
            "features": feature_list,
            "pipeline": pipeline,
            "weights": coefficients,
            "intercept": float(ridge.intercept_),
            "alpha": float(alpha),
            "train_samples": int(len(working)),
            "train_score": float(pipeline.score(train_x, train_y)),
        }
