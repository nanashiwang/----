from __future__ import annotations

from dataclasses import dataclass

from ml.datasets.tag_encoder import TAG_ENCODER_VERSION, TagFeatureEncoder


@dataclass(slots=True)
class FeatureBuildResult:
    rows: list[dict]
    feature_columns: list[str]
    numeric_feature_columns: list[str]
    taxonomy_feature_columns: list[str]
    experiment_mode: str
    tag_encoder_version: str


class FeatureBuilder:
    DEFAULT_FEATURE_COLUMNS = [
        'close',
        'pct_chg',
        'turnover_rate',
        'volume_ratio',
        'ma5_bias',
        'ma20_bias',
        'rsi14',
        'macd_hist',
    ]

    def __init__(self, tag_encoder: TagFeatureEncoder | None = None):
        self.tag_encoder = tag_encoder or TagFeatureEncoder()

    def build(
        self,
        dataset: list[dict],
        *,
        experiment_mode: str = 'baseline',
        tag_encoder_version: str = TAG_ENCODER_VERSION,
    ) -> FeatureBuildResult:
        numeric_feature_columns = [
            column for column in self.DEFAULT_FEATURE_COLUMNS if any(column in row for row in dataset)
        ]
        normalized_rows = []
        for row in dataset:
            item = dict(row)
            for column in numeric_feature_columns:
                item[column] = float(item.get(column, 0.0) or 0.0)
            normalized_rows.append(item)

        taxonomy_feature_columns: list[str] = []
        if experiment_mode == 'hybrid':
            encoded = self.tag_encoder.transform(normalized_rows)
            normalized_rows = encoded.rows
            taxonomy_feature_columns = encoded.feature_columns

        return FeatureBuildResult(
            rows=normalized_rows,
            feature_columns=numeric_feature_columns + taxonomy_feature_columns,
            numeric_feature_columns=numeric_feature_columns,
            taxonomy_feature_columns=taxonomy_feature_columns,
            experiment_mode=experiment_mode,
            tag_encoder_version=tag_encoder_version,
        )
