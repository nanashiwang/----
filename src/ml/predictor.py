from typing import Dict

import pandas as pd

from .registry import DEFAULT_SCORE_COLUMN


class LinearFactorPredictor:
    """把训练好的线性因子权重映射为横截面分数。"""

    def predict(
        self,
        dataset: pd.DataFrame,
        model: Dict,
        score_col: str = DEFAULT_SCORE_COLUMN,
    ) -> pd.DataFrame:
        if dataset.empty:
            return dataset

        scored = dataset.copy()
        scored[score_col] = 0.0
        for feature in model.get("features", []):
            if feature not in scored.columns:
                continue
            mean_value = model.get("means", {}).get(feature, 0.0)
            std_value = model.get("stds", {}).get(feature, 1.0) or 1.0
            weight = model.get("weights", {}).get(feature, 0.0)
            z_score = (pd.to_numeric(scored[feature], errors="coerce") - mean_value) / std_value
            scored[score_col] = scored[score_col] + z_score.fillna(0.0) * weight
        return scored


class SklearnModelPredictor:
    """使用 scikit-learn pipeline 产出横截面分数。"""

    def predict(
        self,
        dataset: pd.DataFrame,
        model: Dict,
        score_col: str = DEFAULT_SCORE_COLUMN,
    ) -> pd.DataFrame:
        if dataset.empty:
            return dataset

        pipeline = model.get("pipeline")
        features = model.get("features", [])
        if pipeline is None or not features:
            raise ValueError("预测失败：sklearn 模型尚未训练完成")

        scored = dataset.copy()
        predict_x = scored[features].apply(pd.to_numeric, errors="coerce")
        scored[score_col] = pipeline.predict(predict_x)
        return scored
