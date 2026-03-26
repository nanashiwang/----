from __future__ import annotations

from dataclasses import dataclass

from core.enums import SnapshotType
from domain.taxonomy import TAXONOMY_VERSION, normalize_tags


@dataclass(slots=True)
class DatasetBuildResult:
    rows: list[dict]
    taxonomy_version: str
    tag_sources: dict[str, str]


class DatasetBuilder:
    def __init__(self, feature_snapshot_repository, daily_brief_repository=None):
        self.feature_snapshot_repository = feature_snapshot_repository
        self.daily_brief_repository = daily_brief_repository

    def build(self, as_of_date, symbols: list[str] | None = None) -> DatasetBuildResult:
        market_rows = self.feature_snapshot_repository.list_by_date(as_of_date, snapshot_type=SnapshotType.MARKET)
        indicator_rows = self.feature_snapshot_repository.list_by_date(as_of_date, snapshot_type=SnapshotType.INDICATOR)
        market_map = {row.symbol: row.features_json for row in market_rows}
        indicator_map = {row.symbol: row.features_json for row in indicator_rows}
        brief = self.daily_brief_repository.latest_for_date(as_of_date) if self.daily_brief_repository else None
        brief_event_tags = normalize_tags((brief.evidence_json or {}).get('normalized_event_tags', [])) if brief else []

        universe = symbols or sorted(set(market_map) | set(indicator_map))
        records = []
        for symbol in universe:
            market_features = dict(market_map.get(symbol, {}))
            indicator_features = dict(indicator_map.get(symbol, {}))
            record = {'symbol': symbol, 'as_of_date': as_of_date.isoformat()}
            record.update(market_features)
            record.update(indicator_features)
            record['normalized_event_tags'] = brief_event_tags
            record['technical_pattern_tags'] = normalize_tags(indicator_features.get('technical_pattern_tags', []))
            record['risk_pattern_tags'] = normalize_tags(
                list(market_features.get('risk_pattern_tags', [])) + list(indicator_features.get('risk_pattern_tags', []))
            )
            record['market_regime_tags'] = normalize_tags(
                list(market_features.get('market_regime_tags', [])) + list(indicator_features.get('market_regime_tags', []))
            )
            record['sentiment_state_tags'] = normalize_tags(market_features.get('sentiment_state_tags', []))
            record['breadth_state_tags'] = normalize_tags(market_features.get('breadth_state_tags', []))
            record['target_return'] = float(record.get('pct_chg', 0.0)) / 100.0 if 'pct_chg' in record else 0.0
            records.append(record)

        return DatasetBuildResult(
            rows=records,
            taxonomy_version=TAXONOMY_VERSION,
            tag_sources={
                'normalized_event_tags': 'daily_briefs.evidence_json.normalized_event_tags',
                'technical_pattern_tags': 'feature_snapshots.indicator.features_json.technical_pattern_tags',
                'risk_pattern_tags': 'feature_snapshots.market_or_indicator.features_json.risk_pattern_tags',
                'market_regime_tags': 'feature_snapshots.market.features_json.market_regime_tags',
                'sentiment_state_tags': 'feature_snapshots.market.features_json.sentiment_state_tags',
                'breadth_state_tags': 'feature_snapshots.market.features_json.breadth_state_tags',
            },
        )
