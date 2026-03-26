from __future__ import annotations

from core.enums import RecommendationAction, RiskLevel, SnapshotType
from domain.messages import AgentResult
from domain.schemas import CandidateOut, ColdKnowledge, EvidenceRef, FlowState
from domain.taxonomy import (
    aggregate_normalized_event_tags,
    match_structured_tags,
    normalize_tags,
)
from agents.arbitration import ArbitrationService
from workflows.base import BaseFlowRunner


class ReasonFlowRunner(BaseFlowRunner):
    flow_name = 'reason'
    node_sequence = (
        'load_evidence_pack',
        'initial_screening',
        'load_active_cold_knowledge',
        'bull_case_agent',
        'bear_case_agent',
        'technical_analyst_agent',
        'apply_knowledge_arbitration',
        'moderator_agent',
        'final_selector_agent',
        'persist_recommendations',
    )

    def __init__(self, deps):
        super().__init__(deps)
        self.arbitration_service = ArbitrationService()

    def load_evidence_pack(self, state: FlowState) -> FlowState:
        if not state.daily_brief:
            brief = self.deps.daily_brief_repository.latest_for_date(state.as_of_date)
            state.daily_brief = brief.content if brief else 'No daily brief available.'
            if brief is not None:
                state.metadata['daily_brief_event_tags'] = normalize_tags(
                    brief.evidence_json.get('normalized_event_tags', [])
                )
        if not state.market_snapshots:
            rows = self.deps.feature_snapshot_repository.list_by_date(state.as_of_date, snapshot_type=SnapshotType.MARKET)
            state.market_snapshots = {row.symbol: row.features_json for row in rows}
        if not state.indicator_snapshots:
            rows = self.deps.feature_snapshot_repository.list_by_date(state.as_of_date, snapshot_type=SnapshotType.INDICATOR)
            state.indicator_snapshots = {row.symbol: row.features_json for row in rows}
        if not state.news_articles:
            articles = self.deps.news_repository.list_recent(state.as_of_date, hours=24)
            state.news_articles = [
                {
                    'article_id': article.article_id,
                    'title': article.title,
                    'source': article.source,
                    'url': article.url,
                    'published_at': article.published_at,
                    'summary': article.summary,
                    'content': article.content,
                    'symbols': (article.symbols_json or {}).get('symbols', []),
                    'raw_event_tags': (article.metadata_json or {}).get('raw_event_tags', []),
                    'normalized_event_tags': normalize_tags(
                        (article.metadata_json or {}).get('normalized_event_tags', [])
                    ),
                }
                for article in articles
            ]
        state.evidence_pack = [
            EvidenceRef(
                ref_id=f"article:{article['article_id']}",
                ref_type='news_article',
                title=article['title'],
                source=article['source'],
                url=article['url'],
                symbol=(article.get('symbols') or [None])[0],
                excerpt=article['summary'] or article['content'][:120],
                published_at=article.get('published_at'),
                metadata={
                    'raw_event_tags': article.get('raw_event_tags', []),
                    'normalized_event_tags': article.get('normalized_event_tags', []),
                },
            )
            for article in state.news_articles[:8]
        ]
        state.metadata['normalized_event_tags'] = aggregate_normalized_event_tags(state.news_articles)
        return state

    def initial_screening(self, state: FlowState) -> FlowState:
        candidates = []
        for symbol, snapshot in list(state.market_snapshots.items())[:5]:
            indicator = state.indicator_snapshots.get(symbol, {})
            ml_score = min(1.0, 0.45 + float(snapshot.get('turnover_rate', 0)) / 10.0)
            event_score = min(1.0, 0.4 + len(state.evidence_pack) * 0.03)
            technical_score = min(1.0, 0.4 + float(indicator.get('ma5_bias', 0)) + float(indicator.get('macd_hist', 0)))
            candidates.append(
                CandidateOut(
                    symbol=symbol,
                    action=RecommendationAction.WATCH,
                    weight=0.0,
                    ml_score=round(ml_score, 4),
                    event_score=round(event_score, 4),
                    technical_score=round(technical_score, 4),
                    debate_consensus_score=0.0,
                    risk_adjusted_score=0.5,
                    final_score=0.0,
                    risk_level=RiskLevel.MEDIUM,
                    risk_flags=[],
                    reason='Initial screening candidate.',
                    evidence_refs=state.evidence_pack[:3],
                    market_regime_tags=normalize_tags(snapshot.get('market_regime_tags', [])),
                    event_tags=self._collect_candidate_event_tags(state, symbol),
                    technical_pattern_tags=normalize_tags(indicator.get('technical_pattern_tags', [])),
                    risk_pattern_tags=normalize_tags(
                        snapshot.get('risk_pattern_tags', []) + indicator.get('risk_pattern_tags', [])
                    ),
                )
            )
        state.candidates = candidates
        return state

    def load_active_cold_knowledge(self, state: FlowState) -> FlowState:
        cold_rows = self.deps.knowledge_repository.get_active_cold_knowledge(limit=200)
        cold_knowledge = [ColdKnowledge.model_validate(item) for item in cold_rows]
        state.metadata['active_cold_knowledge'] = [item.model_dump(mode='json') for item in cold_knowledge]
        state.metadata['active_cold_knowledge_count'] = len(cold_knowledge)
        return state

    def bull_case_agent(self, state: FlowState) -> FlowState:
        return self._append_agent_view(state, 'bull_case_agent', stance='bullish')

    def bear_case_agent(self, state: FlowState) -> FlowState:
        return self._append_agent_view(state, 'bear_case_agent', stance='bearish')

    def technical_analyst_agent(self, state: FlowState) -> FlowState:
        return self._append_agent_view(state, 'technical_analyst_agent', stance='technical')

    def apply_knowledge_arbitration(self, state: FlowState) -> FlowState:
        cold_knowledge = [
            ColdKnowledge.model_validate(item)
            for item in state.metadata.get('active_cold_knowledge', [])
        ]
        if not cold_knowledge:
            state.metadata['matched_cold_knowledge_count'] = 0
            state.metadata['knowledge_adjusted_recommendation_count'] = 0
            return state

        matched_knowledge_ids: set[str] = set()
        adjusted_candidate_count = 0

        for candidate in state.candidates:
            knowledge_refs: list[EvidenceRef] = []
            knowledge_impacts: list[dict] = []
            support_hits = 0
            penalty_hits = 0

            for knowledge in cold_knowledge:
                impact = self._match_knowledge(candidate, knowledge)
                if impact is None:
                    continue

                matched_knowledge_ids.add(knowledge.knowledge_id)
                knowledge_refs.append(self._build_knowledge_ref(knowledge, impact))
                knowledge_impacts.append(impact)

                if impact['impact_type'] == 'support':
                    candidate.knowledge_match_score = round(
                        min(0.20, candidate.knowledge_match_score + impact['impact_score']),
                        4,
                    )
                    support_hits += 1
                else:
                    candidate.knowledge_risk_penalty = round(
                        min(0.25, candidate.knowledge_risk_penalty + impact['impact_score']),
                        4,
                    )
                    penalty_hits += 1
                    if impact.get('high_risk'):
                        candidate.risk_flags.append('knowledge_high_risk')

                if impact.get('conflicting_tags'):
                    candidate.risk_flags.append('knowledge_conflict')

            candidate.knowledge_refs = knowledge_refs
            candidate.knowledge_impact_json = knowledge_impacts
            candidate.knowledge_conflict_flag = bool(
                penalty_hits and support_hits or any(item.get('conflicting_tags') for item in knowledge_impacts)
            )
            if candidate.knowledge_conflict_flag:
                candidate.risk_flags.append('knowledge_conflict')
                if 'risk_pattern:event_conflict_risk' not in candidate.risk_pattern_tags:
                    candidate.risk_pattern_tags.append('risk_pattern:event_conflict_risk')

            candidate.risk_flags = list(dict.fromkeys(candidate.risk_flags))
            candidate.risk_pattern_tags = normalize_tags(candidate.risk_pattern_tags)
            if knowledge_impacts:
                adjusted_candidate_count += 1

        state.metadata['matched_cold_knowledge_count'] = len(matched_knowledge_ids)
        state.metadata['knowledge_adjusted_recommendation_count'] = adjusted_candidate_count
        state.metadata['matched_cold_knowledge_ids'] = sorted(matched_knowledge_ids)
        return state

    def moderator_agent(self, state: FlowState) -> FlowState:
        for candidate in state.candidates:
            symbol_results = state.agent_results.get(candidate.symbol, [])
            if not symbol_results:
                continue
            avg_score = sum(item['score'] for item in symbol_results) / len(symbol_results)
            candidate.debate_consensus_score = round(avg_score, 4)
            if avg_score < 0.4:
                candidate.risk_flags.append('weak_consensus')
            if candidate.technical_score < 0.45:
                candidate.risk_flags.append('technical_headwind')
            if candidate.knowledge_conflict_flag:
                candidate.risk_flags.append('knowledge_conflict')
                candidate.debate_consensus_score = round(max(0.0, candidate.debate_consensus_score - 0.05), 4)
        return state

    def final_selector_agent(self, state: FlowState) -> FlowState:
        recommendations = []
        for candidate in state.candidates:
            candidate.risk_adjusted_score = 0.30 if 'technical_headwind' in candidate.risk_flags else 0.75
            if 'knowledge_high_risk' in candidate.risk_flags:
                candidate.risk_adjusted_score = min(candidate.risk_adjusted_score, 0.25)
            if candidate.knowledge_conflict_flag:
                candidate.risk_adjusted_score = min(candidate.risk_adjusted_score, 0.45)
            if 'weak_consensus' in candidate.risk_flags or 'knowledge_high_risk' in candidate.risk_flags:
                candidate.risk_level = RiskLevel.HIGH
            arbitration = self.arbitration_service.arbitrate(candidate)
            recommendations.append(
                candidate.model_copy(
                    update={
                        'action': arbitration.action,
                        'final_score': arbitration.final_score,
                        'weight': round(arbitration.final_score, 4),
                        'reason': arbitration.explanation,
                        'risk_level': arbitration.risk_level,
                        'risk_flags': arbitration.risk_flags,
                    }
                )
            )
        state.recommendations = recommendations
        return state

    def persist_recommendations(self, state: FlowState) -> FlowState:
        artifact_rows = []
        recommendation_rows = []
        for candidate in state.recommendations:
            evidence_refs = [item.model_dump(mode='json') for item in candidate.evidence_refs]
            knowledge_refs = [item.model_dump(mode='json') for item in candidate.knowledge_refs]
            if candidate.action == RecommendationAction.INCLUDE and not evidence_refs:
                raise ValueError(f'include recommendation requires evidence_refs: {candidate.symbol}')
            artifact_rows.append(
                {
                    'run_id': state.run_id,
                    'symbol': candidate.symbol,
                    'model_version': state.model_version,
                    'feature_set_version': state.feature_set_version,
                    'ml_score': candidate.ml_score,
                    'event_score': candidate.event_score,
                    'technical_score': candidate.technical_score,
                    'debate_consensus_score': candidate.debate_consensus_score,
                    'risk_adjusted_score': candidate.risk_adjusted_score,
                    'final_score': candidate.final_score,
                    'artifact_uri': f'artifacts/{state.run_id}/{candidate.symbol}.json',
                    'explanation_json': {
                        'reason': candidate.reason,
                        'knowledge_impact_json': candidate.knowledge_impact_json,
                        'knowledge_match_score': candidate.knowledge_match_score,
                        'knowledge_risk_penalty': candidate.knowledge_risk_penalty,
                    },
                    'evidence_json': {
                        'evidence_refs': evidence_refs,
                        'knowledge_refs': knowledge_refs,
                        'knowledge_impact_json': candidate.knowledge_impact_json,
                        'normalized_event_tags': candidate.event_tags,
                        'event_tags': candidate.event_tags,
                        'technical_pattern_tags': candidate.technical_pattern_tags,
                        'risk_pattern_tags': candidate.risk_pattern_tags,
                        'market_regime_tags': candidate.market_regime_tags,
                    },
                }
            )
        artifacts = self.deps.prediction_artifact_repository.bulk_create(artifact_rows)
        for artifact, candidate in zip(artifacts, state.recommendations):
            evidence_refs = [item.model_dump(mode='json') for item in candidate.evidence_refs]
            knowledge_refs = [item.model_dump(mode='json') for item in candidate.knowledge_refs]
            recommendation_rows.append(
                {
                    'run_id': state.run_id,
                    'prediction_artifact_id': artifact.artifact_id,
                    'symbol': candidate.symbol,
                    'action': candidate.action,
                    'weight': candidate.weight,
                    'final_score': candidate.final_score,
                    'reason': candidate.reason,
                    'risk_flags_json': {
                        'risk_flags': candidate.risk_flags,
                        'knowledge_conflict_flag': candidate.knowledge_conflict_flag,
                    },
                    'evidence_json': {
                        'evidence_refs': evidence_refs,
                        'knowledge_refs': knowledge_refs,
                        'knowledge_impact_json': candidate.knowledge_impact_json,
                        'knowledge_match_score': candidate.knowledge_match_score,
                        'knowledge_risk_penalty': candidate.knowledge_risk_penalty,
                        'knowledge_conflict_flag': candidate.knowledge_conflict_flag,
                        'normalized_event_tags': candidate.event_tags,
                        'event_tags': candidate.event_tags,
                        'technical_pattern_tags': candidate.technical_pattern_tags,
                        'risk_pattern_tags': candidate.risk_pattern_tags,
                        'market_regime_tags': candidate.market_regime_tags,
                    },
                }
            )
        self.deps.recommendation_repository.bulk_create(recommendation_rows)
        state.metadata['persisted_recommendation_count'] = len(recommendation_rows)
        state.metadata['knowledge_adjusted_recommendation_count'] = sum(
            1 for candidate in state.recommendations if candidate.knowledge_impact_json
        )
        state.prediction_artifacts = artifact_rows
        return state

    def _append_agent_view(self, state: FlowState, role: str, stance: str) -> FlowState:
        for candidate in state.candidates:
            context = {
                'base_score': (candidate.ml_score + candidate.event_score + candidate.technical_score) / 3,
                'brief': state.daily_brief,
                'market': state.market_snapshots.get(candidate.symbol, {}),
                'indicator': state.indicator_snapshots.get(candidate.symbol, {}),
                'event_tags': candidate.event_tags,
                'technical_pattern_tags': candidate.technical_pattern_tags,
                'market_regime_tags': candidate.market_regime_tags,
            }
            llm_result = self.deps.llm_provider.build_argument(role, candidate.symbol, context)
            result = AgentResult(
                agent_name=role,
                run_id=state.run_id,
                symbol=candidate.symbol,
                stance=stance,
                score=float(llm_result.get('score', 0.5)),
                summary=llm_result.get('summary', ''),
                risk_level=candidate.risk_level,
                risk_flags=list(candidate.risk_flags),
                evidence_refs=candidate.evidence_refs,
                payload=context,
            )
            state.agent_results.setdefault(candidate.symbol, []).append(result.model_dump(mode='json'))
            state.agent_messages.append(
                {
                    'sender': role,
                    'receiver': 'moderator_agent',
                    'symbol': candidate.symbol,
                    'payload': {'summary': result.summary, 'score': result.score},
                }
            )
        return state

    def _collect_candidate_event_tags(self, state: FlowState, symbol: str) -> list[str]:
        symbol_specific_tags: list[str] = []
        fallback_tags = normalize_tags(state.metadata.get('daily_brief_event_tags', []))

        for article in state.news_articles:
            normalized_event_tags = normalize_tags(article.get('normalized_event_tags', []))
            symbols = [str(item).upper() for item in article.get('symbols', [])]
            if symbol.upper() in symbols:
                for tag in normalized_event_tags:
                    if tag not in symbol_specific_tags:
                        symbol_specific_tags.append(tag)
            else:
                for tag in normalized_event_tags:
                    if tag not in fallback_tags:
                        fallback_tags.append(tag)

        return symbol_specific_tags or fallback_tags

    def _match_knowledge(self, candidate: CandidateOut, knowledge: ColdKnowledge) -> dict | None:
        tag_match = match_structured_tags(
            candidate_event_tags=candidate.event_tags,
            candidate_technical_tags=candidate.technical_pattern_tags,
            candidate_market_regime_tags=candidate.market_regime_tags,
            candidate_risk_tags=candidate.risk_pattern_tags,
            applicable_event_tags=knowledge.applicable_event_tags,
            applicable_technical_tags=knowledge.applicable_technical_tags,
            applicable_market_regimes=knowledge.applicable_market_regimes,
            negative_match_tags=knowledge.negative_match_tags,
        )
        if tag_match.match_score <= 0 and not tag_match.conflicting_tags:
            return None

        is_risk_knowledge = any(
            keyword in knowledge.category.lower()
            for keyword in ('failure', 'risk', 'data_quality')
        )
        impact_type = 'risk_penalty' if is_risk_knowledge else 'support'
        base_impact = min(0.18, 0.04 + tag_match.match_score * 0.12)
        high_risk = False
        if impact_type == 'risk_penalty':
            base_impact += 0.03 if tag_match.conflicting_tags else 0.0
            high_risk = bool(tag_match.conflicting_tags or tag_match.match_score >= 0.65)
        else:
            if tag_match.conflicting_tags:
                base_impact = max(0.0, base_impact - 0.04)

        impact_score = round(max(0.0, min(0.20, base_impact)), 4)
        if impact_score <= 0:
            return None

        return {
            'knowledge_id': knowledge.knowledge_id,
            'impact_type': impact_type,
            'impact_score': impact_score,
            'reason': (
                f"match_score={tag_match.match_score:.2f}; "
                f"matched_tags={tag_match.matched_tags}; "
                f"missing_required_tags={tag_match.missing_required_tags}; "
                f"conflicting_tags={tag_match.conflicting_tags}"
            ),
            'category': knowledge.category,
            'matched_tags': tag_match.matched_tags,
            'missing_required_tags': tag_match.missing_required_tags,
            'conflicting_tags': tag_match.conflicting_tags,
            'match_score': tag_match.match_score,
            'high_risk': high_risk,
        }

    @staticmethod
    def _build_knowledge_ref(knowledge: ColdKnowledge, impact: dict) -> EvidenceRef:
        return EvidenceRef(
            ref_id=knowledge.knowledge_id,
            ref_type='cold_knowledge',
            title=knowledge.category,
            source='cold_knowledge',
            excerpt=knowledge.text,
            score=float(impact.get('impact_score', 0.0)),
            metadata={
                'promotion_run_id': knowledge.promotion_run_id,
                'pass_rate': knowledge.pass_rate,
                'tests_survived': knowledge.tests_survived,
                'impact_type': impact.get('impact_type'),
                'matched_tags': impact.get('matched_tags', []),
                'conflicting_tags': impact.get('conflicting_tags', []),
                'match_score': impact.get('match_score', 0.0),
            },
        )
