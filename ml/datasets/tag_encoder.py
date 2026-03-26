from __future__ import annotations

from dataclasses import dataclass

from ml.features.taxonomy_features import TAXONOMY_TAG_FIELDS, extract_taxonomy_feature_record


TAG_ENCODER_VERSION = 'tag-encoder-v1'


@dataclass(slots=True)
class TagEncodingResult:
    rows: list[dict]
    feature_columns: list[str]
    vocabulary: list[str]
    interaction_columns: list[str]
    tag_count_columns: list[str]


class TagFeatureEncoder:
    VERSION = TAG_ENCODER_VERSION

    def fit(self, dataset: list[dict]) -> list[str]:
        vocabulary: set[str] = set()
        for row in dataset:
            record = extract_taxonomy_feature_record(row)
            for field_name in TAXONOMY_TAG_FIELDS:
                vocabulary.update(getattr(record, field_name))
        return sorted(vocabulary)

    def transform(self, dataset: list[dict], vocabulary: list[str] | None = None) -> TagEncodingResult:
        vocabulary = vocabulary or self.fit(dataset)
        interaction_columns = [
            'interaction:event_type:sector_rotation__trend_state:short_term_uptrend',
            'interaction:event_direction:bullish__breakout_state:breakout_confirmed',
            'interaction:market_regime:benchmark_downtrend__risk_pattern:high_volatility_risk',
        ]
        tag_count_columns = [f'tag_count:{field_name}' for field_name in TAXONOMY_TAG_FIELDS]
        encoded_rows: list[dict] = []

        for row in dataset:
            item = dict(row)
            record = extract_taxonomy_feature_record(item)
            tag_map = record.as_dict()
            tag_set = set()
            for field_name, tags in tag_map.items():
                tag_set.update(tags)
                item[field_name] = tags
                item[f'tag_count:{field_name}'] = float(len(tags))

            for tag in vocabulary:
                item[tag] = 1.0 if tag in tag_set else 0.0

            item[interaction_columns[0]] = float(
                'event_type:sector_rotation' in tag_set and 'trend_state:short_term_uptrend' in tag_set
            )
            item[interaction_columns[1]] = float(
                'event_direction:bullish' in tag_set and 'breakout_state:breakout_confirmed' in tag_set
            )
            item[interaction_columns[2]] = float(
                'market_regime:benchmark_downtrend' in tag_set and 'risk_pattern:high_volatility_risk' in tag_set
            )
            encoded_rows.append(item)

        return TagEncodingResult(
            rows=encoded_rows,
            feature_columns=vocabulary + tag_count_columns + interaction_columns,
            vocabulary=vocabulary,
            interaction_columns=interaction_columns,
            tag_count_columns=tag_count_columns,
        )
