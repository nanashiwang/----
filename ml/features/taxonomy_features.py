from __future__ import annotations

from dataclasses import dataclass

from domain.taxonomy import normalize_tags


TAXONOMY_TAG_FIELDS = (
    'normalized_event_tags',
    'technical_pattern_tags',
    'risk_pattern_tags',
    'market_regime_tags',
    'sentiment_state_tags',
    'breadth_state_tags',
)


@dataclass(slots=True)
class TaxonomyFeatureRecord:
    normalized_event_tags: list[str]
    technical_pattern_tags: list[str]
    risk_pattern_tags: list[str]
    market_regime_tags: list[str]
    sentiment_state_tags: list[str]
    breadth_state_tags: list[str]

    def as_dict(self) -> dict[str, list[str]]:
        return {
            'normalized_event_tags': self.normalized_event_tags,
            'technical_pattern_tags': self.technical_pattern_tags,
            'risk_pattern_tags': self.risk_pattern_tags,
            'market_regime_tags': self.market_regime_tags,
            'sentiment_state_tags': self.sentiment_state_tags,
            'breadth_state_tags': self.breadth_state_tags,
        }


def extract_taxonomy_feature_record(row: dict) -> TaxonomyFeatureRecord:
    return TaxonomyFeatureRecord(
        normalized_event_tags=normalize_tags(row.get('normalized_event_tags', [])),
        technical_pattern_tags=normalize_tags(row.get('technical_pattern_tags', [])),
        risk_pattern_tags=normalize_tags(row.get('risk_pattern_tags', [])),
        market_regime_tags=normalize_tags(row.get('market_regime_tags', [])),
        sentiment_state_tags=normalize_tags(row.get('sentiment_state_tags', [])),
        breadth_state_tags=normalize_tags(row.get('breadth_state_tags', [])),
    )
