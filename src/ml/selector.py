from typing import Dict, Iterable, List, Optional

import pandas as pd

from .registry import DEFAULT_FEATURE_COLUMNS, DEFAULT_LABEL_COLUMN


class FeatureSelector:
    """第一版指标筛选器：缺失率、低方差、高相关去重、IC 排序。"""

    def select(
        self,
        dataset: pd.DataFrame,
        candidate_features: Optional[Iterable[str]] = None,
        label_col: str = DEFAULT_LABEL_COLUMN,
        top_k: int = 6,
        max_missing_rate: float = 0.35,
        min_std: float = 1e-8,
        max_correlation: float = 0.9,
        min_samples: int = 20,
    ) -> Dict:
        if dataset.empty:
            return {"selected_features": [], "feature_stats": [], "label_col": label_col}

        features = [item for item in (candidate_features or DEFAULT_FEATURE_COLUMNS) if item in dataset.columns]
        if not features:
            return {"selected_features": [], "feature_stats": [], "label_col": label_col}

        stats: List[Dict] = []
        eligible_features: List[str] = []
        for feature in features:
            valid = dataset[[feature, label_col]].dropna()
            missing_rate = float(dataset[feature].isna().mean())
            std_value = float(valid[feature].std(ddof=0)) if len(valid) > 1 else 0.0
            ic = self._rank_ic(valid[feature], valid[label_col]) if len(valid) >= min_samples else 0.0
            stats.append(
                {
                    "feature": feature,
                    "missing_rate": missing_rate,
                    "std": std_value,
                    "ic": ic,
                    "usable_samples": int(len(valid)),
                }
            )
            if missing_rate <= max_missing_rate and std_value > min_std:
                eligible_features.append(feature)

        ranked_stats = sorted(
            [item for item in stats if item["feature"] in eligible_features],
            key=lambda item: abs(item["ic"]),
            reverse=True,
        )

        selected: List[str] = []
        if eligible_features:
            corr_source = dataset[eligible_features].corr().abs()
            for item in ranked_stats:
                feature = item["feature"]
                if selected and any(corr_source.loc[feature, chosen] >= max_correlation for chosen in selected):
                    continue
                selected.append(feature)
                if len(selected) >= top_k:
                    break

        if not selected and ranked_stats:
            selected = [ranked_stats[0]["feature"]]

        return {
            "selected_features": selected,
            "feature_stats": sorted(stats, key=lambda item: abs(item["ic"]), reverse=True),
            "label_col": label_col,
        }

    def _rank_ic(self, feature_series: pd.Series, label_series: pd.Series) -> float:
        if len(feature_series) < 2:
            return 0.0
        ranked = pd.DataFrame({"feature": feature_series, "label": label_series}).rank()
        value = ranked["feature"].corr(ranked["label"])
        return float(value) if pd.notna(value) else 0.0
