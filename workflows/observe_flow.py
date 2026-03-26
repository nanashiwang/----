from __future__ import annotations

from core.enums import SnapshotType
from domain.schemas import EvidenceRef, FlowState
from domain.taxonomy import (
    aggregate_normalized_event_tags,
    derive_article_event_tags,
    derive_global_market_context_tags,
    derive_snapshot_taxonomy,
)
from workflows.base import BaseFlowRunner


class ObserveFlowRunner(BaseFlowRunner):
    flow_name = 'observe'
    node_sequence = (
        'ingest_news_articles',
        'build_daily_brief',
        'load_watchlist_symbols',
        'build_market_snapshot',
        'build_indicator_snapshot',
        'finalize_observe',
    )

    def ingest_news_articles(self, state: FlowState) -> FlowState:
        articles = self.deps.market_data_client.fetch_hot_news(state.as_of_date, hours=24)
        persisted = []
        for article in articles:
            article['ingested_run_id'] = state.run_id
            tag_payload = derive_article_event_tags(article)
            article['raw_event_tags'] = tag_payload['raw_event_tags']
            article['normalized_event_tags'] = tag_payload['normalized_event_tags']
            article['metadata'] = {
                **dict(article.get('metadata', {})),
                'raw_event_tags': article['raw_event_tags'],
                'normalized_event_tags': article['normalized_event_tags'],
            }
            persisted_article = self.deps.news_repository.upsert_article(article)
            persisted.append(
                {
                    'article_id': persisted_article.article_id,
                    'title': persisted_article.title,
                    'source': persisted_article.source,
                    'url': persisted_article.url,
                    'published_at': persisted_article.published_at,
                    'summary': persisted_article.summary,
                    'content': persisted_article.content,
                    'symbols': article.get('symbols', []),
                    'raw_event_tags': article['raw_event_tags'],
                    'normalized_event_tags': article['normalized_event_tags'],
                }
            )
        state.news_articles = persisted
        return state

    def build_daily_brief(self, state: FlowState) -> FlowState:
        history_rows = self.deps.daily_brief_repository.list_history(state.as_of_date, limit=30)
        state.historical_briefs = [
            {'brief_id': row.brief_id, 'as_of_date': row.as_of_date.isoformat(), 'content': row.content}
            for row in history_rows
        ]
        content = self.deps.llm_provider.summarize_daily_brief(state.news_articles, state.historical_briefs)
        evidence_json = {
            'article_ids': [article['article_id'] for article in state.news_articles],
            'raw_event_tags': [article.get('raw_event_tags', []) for article in state.news_articles],
            'normalized_event_tags': aggregate_normalized_event_tags(state.news_articles),
        }
        self.deps.daily_brief_repository.upsert_brief(
            run_id=state.run_id,
            as_of_date=state.as_of_date,
            brief_type='daily_brief',
            prompt_version=state.prompt_version,
            model_version=state.model_version,
            content=content,
            evidence_json=evidence_json,
        )
        state.daily_brief = content
        return state

    def load_watchlist_symbols(self, state: FlowState) -> FlowState:
        state.watchlist_symbols = state.watchlist_symbols or self.deps.market_data_client.get_watchlist_symbols()
        return state

    def build_market_snapshot(self, state: FlowState) -> FlowState:
        snapshots = self.deps.market_data_client.fetch_market_snapshot(state.watchlist_symbols, state.as_of_date)
        global_market_context = derive_global_market_context_tags(snapshots.values())
        enriched_snapshots = {}
        for symbol, features in snapshots.items():
            taxonomy_payload = derive_snapshot_taxonomy(features, {}, global_market_context)
            enriched_features = {
                **features,
                'market_regime_tags': taxonomy_payload['market_regime_tags'],
                'sentiment_state_tags': taxonomy_payload['sentiment_state_tags'],
                'breadth_state_tags': taxonomy_payload['breadth_state_tags'],
                'risk_pattern_tags': taxonomy_payload['risk_pattern_tags'],
            }
            self.deps.feature_snapshot_repository.upsert_snapshot(
                run_id=state.run_id,
                as_of_date=state.as_of_date,
                symbol=symbol,
                snapshot_type=SnapshotType.MARKET,
                feature_set_version=state.feature_set_version,
                features_json=enriched_features,
                evidence_json={'source': 'market_snapshot', **taxonomy_payload},
            )
            enriched_snapshots[symbol] = enriched_features
        state.market_snapshots = enriched_snapshots
        state.metadata['global_market_context'] = global_market_context
        return state

    def build_indicator_snapshot(self, state: FlowState) -> FlowState:
        snapshots = self.deps.market_data_client.fetch_indicator_snapshot(state.watchlist_symbols, state.as_of_date)
        global_market_context = state.metadata.get('global_market_context') or derive_global_market_context_tags(
            state.market_snapshots.values()
        )
        enriched_snapshots = {}
        for symbol, features in snapshots.items():
            taxonomy_payload = derive_snapshot_taxonomy(
                state.market_snapshots.get(symbol, {}),
                features,
                global_market_context,
            )
            enriched_features = {
                **features,
                'technical_pattern_tags': taxonomy_payload['technical_pattern_tags'],
                'risk_pattern_tags': taxonomy_payload['risk_pattern_tags'],
                'market_regime_tags': taxonomy_payload['market_regime_tags'],
                'sentiment_state_tags': taxonomy_payload['sentiment_state_tags'],
                'breadth_state_tags': taxonomy_payload['breadth_state_tags'],
            }
            self.deps.feature_snapshot_repository.upsert_snapshot(
                run_id=state.run_id,
                as_of_date=state.as_of_date,
                symbol=symbol,
                snapshot_type=SnapshotType.INDICATOR,
                feature_set_version=state.feature_set_version,
                features_json=enriched_features,
                evidence_json={'source': 'indicator_snapshot', **taxonomy_payload},
            )
            if symbol in state.market_snapshots:
                state.market_snapshots[symbol]['risk_pattern_tags'] = taxonomy_payload['risk_pattern_tags']
                state.market_snapshots[symbol]['market_regime_tags'] = taxonomy_payload['market_regime_tags']
            enriched_snapshots[symbol] = enriched_features
        state.indicator_snapshots = enriched_snapshots
        return state

    def finalize_observe(self, state: FlowState) -> FlowState:
        normalized_event_tags = aggregate_normalized_event_tags(state.news_articles)
        state.evidence_pack = [
            EvidenceRef(
                ref_id=f"article:{article['article_id']}",
                ref_type='news_article',
                title=article['title'],
                source=article['source'],
                url=article['url'],
                excerpt=article['summary'] or article['content'][:200],
                published_at=article['published_at'],
                symbol=(article.get('symbols') or [None])[0],
                metadata={
                    'raw_event_tags': article.get('raw_event_tags', []),
                    'normalized_event_tags': article.get('normalized_event_tags', []),
                },
            )
            for article in state.news_articles[:10]
        ]
        state.metadata['daily_evidence_pack'] = {
            'brief': state.daily_brief,
            'article_count': len(state.news_articles),
            'symbol_count': len(state.watchlist_symbols),
            'normalized_event_tags': normalized_event_tags,
        }
        return state
