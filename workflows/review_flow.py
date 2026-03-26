from __future__ import annotations

from datetime import date

from core.enums import KnowledgeStatus, KnowledgeTier, RecommendationAction
from domain.schemas import FlowState, KnowledgeItem, RecommendationVerdict, ReviewVerdict
from domain.taxonomy import normalize_tags
from memory.promotion import KnowledgePromotionService
from workflows.base import BaseFlowRunner


class ReviewFlowRunner(BaseFlowRunner):
    flow_name = 'review'
    node_sequence = (
        'load_prior_recommendations',
        'load_realized_outcomes',
        'compare_prediction_vs_outcome',
        'generate_review_brief',
        'update_hot_knowledge',
        'promote_or_demote_knowledge',
        'finalize_review',
    )

    def __init__(self, deps):
        super().__init__(deps)
        self.promotion_service = KnowledgePromotionService()

    def load_prior_recommendations(self, state: FlowState) -> FlowState:
        target_run_id = state.payload.get('target_run_id') or state.payload.get('recommendation_run_id')
        if not target_run_id:
            raise ValueError('target_run_id is required for review_flow')

        target_run = self.deps.workflow_runs.get(target_run_id)
        if target_run is None:
            raise ValueError(f'target run not found: {target_run_id}')

        rows = self.deps.recommendation_repository.list_by_run(target_run_id)
        horizon = int(state.payload.get('horizon', 5))

        state.metadata['target_run_id'] = target_run_id
        state.metadata['target_as_of_date'] = target_run.as_of_date.isoformat()
        state.metadata['review_horizon'] = horizon
        state.metadata['prior_recommendations'] = [
            {
                'recommendation_id': row.recommendation_id,
                'symbol': row.symbol,
                'action': row.action.value if hasattr(row.action, 'value') else row.action,
                'weight': row.weight,
                'final_score': row.final_score,
                'reason': row.reason,
                'risk_flags_json': row.risk_flags_json,
                'evidence_json': row.evidence_json,
            }
            for row in rows
        ]
        return state

    def load_realized_outcomes(self, state: FlowState) -> FlowState:
        symbols = [item['symbol'] for item in state.metadata.get('prior_recommendations', [])]
        if not symbols:
            state.metadata['realized_outcomes'] = {}
            return state

        target_as_of_date = state.metadata.get('target_as_of_date', state.as_of_date.isoformat())
        outcomes = self.deps.market_data_client.load_realized_outcomes(
            symbols=symbols,
            as_of_date=date.fromisoformat(target_as_of_date) if isinstance(target_as_of_date, str) else target_as_of_date,
            horizon=int(state.metadata.get('review_horizon', 5)),
        )
        state.metadata['realized_outcomes'] = outcomes
        return state

    def compare_prediction_vs_outcome(self, state: FlowState) -> FlowState:
        verdicts = []
        review_errors = []
        horizon = int(state.metadata.get('review_horizon', 5))

        for recommendation in state.metadata.get('prior_recommendations', []):
            outcome = state.metadata.get('realized_outcomes', {}).get(recommendation['symbol'], {})
            verdicts.append(self._build_verdict(recommendation, outcome, horizon, review_errors))

        state.metadata['review_errors'] = review_errors
        state.metadata['verdicts'] = [item.model_dump(mode='json') for item in verdicts]
        if review_errors:
            state.errors.extend(review_errors)
        return state

    def generate_review_brief(self, state: FlowState) -> FlowState:
        horizon = int(state.metadata.get('review_horizon', 5))
        verdicts = [RecommendationVerdict.model_validate(item) for item in state.metadata.get('verdicts', [])]
        outperform_count = sum(1 for item in verdicts if item.verdict == 'outperform')
        underperform_count = sum(1 for item in verdicts if item.verdict == 'underperform')
        insufficient_count = sum(1 for item in verdicts if item.verdict == 'insufficient_data')
        comparable_items = [item for item in verdicts if item.verdict != 'insufficient_data']
        average_return = round(
            sum((item.actual_return_5d if horizon == 5 else item.actual_return_3d if horizon == 3 else item.actual_return_1d) or 0.0 for item in comparable_items)
            / len(comparable_items),
            4,
        ) if comparable_items else 0.0
        average_benchmark = round(
            sum(item.benchmark_return or 0.0 for item in comparable_items) / len(comparable_items),
            4,
        ) if comparable_items else 0.0
        hit_rate = round(outperform_count / len(comparable_items), 4) if comparable_items else 0.0

        summary_text = (
            f'Reviewed {len(verdicts)} recommendations for {horizon}d horizon: '
            f'{outperform_count} outperform, {underperform_count} underperform, '
            f'{insufficient_count} insufficient_data.'
        )
        outcome = 'positive' if outperform_count > underperform_count else 'mixed' if comparable_items else 'insufficient_data'

        state.review_verdict = ReviewVerdict(
            target_run_id=state.metadata.get('target_run_id', ''),
            horizon=horizon,
            summary_text=summary_text,
            verdicts=verdicts,
            outcome=outcome,
            knowledge_actions=[],
            metrics={
                'total_recommendations': len(verdicts),
                'comparable_recommendations': len(comparable_items),
                'outperform_count': outperform_count,
                'underperform_count': underperform_count,
                'insufficient_count': insufficient_count,
                'hit_rate': hit_rate,
                'average_return': average_return,
                'average_benchmark_return': average_benchmark,
                'average_excess_return': round(average_return - average_benchmark, 4),
                'hot_knowledge_updated_count': 0,
                'promoted_count': 0,
                'demoted_count': 0,
                'archived_count': 0,
            },
        )
        return state

    def update_hot_knowledge(self, state: FlowState) -> FlowState:
        if state.review_verdict is None:
            return state

        updated_items: dict[str, KnowledgeItem] = {}
        for verdict in state.review_verdict.verdicts:
            knowledge_item = self._build_knowledge_item(state, verdict)
            if knowledge_item is None:
                continue
            stored = self.deps.knowledge_repository.upsert_hot(
                knowledge_item.model_dump(mode='json'),
                source_run_id=state.run_id,
            )
            updated_items[stored.knowledge_id] = KnowledgeItem.model_validate(
                {
                    'knowledge_id': stored.knowledge_id,
                    'lineage_id': getattr(stored, 'lineage_id', stored.knowledge_id),
                    'text': stored.text,
                    'category': stored.category,
                    'source_run_ids': stored.source_run_ids,
                    'source_recommendation_ids': stored.source_recommendation_ids,
                    'tests_survived': stored.tests_survived,
                    'pass_count': stored.pass_count,
                    'fail_count': stored.fail_count,
                    'pass_rate': stored.pass_rate,
                    'status': stored.status,
                    'applicable_event_tags': getattr(stored, 'applicable_event_tags', []),
                    'applicable_technical_tags': getattr(stored, 'applicable_technical_tags', []),
                    'applicable_market_regimes': getattr(stored, 'applicable_market_regimes', []),
                    'negative_match_tags': getattr(stored, 'negative_match_tags', []),
                    'evidence_json': stored.evidence_json,
                }
            )
        state.knowledge_items = list(updated_items.values())
        state.metadata['hot_knowledge_updated_count'] = len(state.knowledge_items)
        state.metadata['hot_knowledge_ids'] = [item.knowledge_id for item in state.knowledge_items]
        state.review_verdict.metrics['hot_knowledge_updated_count'] = len(state.knowledge_items)
        return state

    def promote_or_demote_knowledge(self, state: FlowState) -> FlowState:
        if state.review_verdict is None:
            return state

        promotion_result = self.promotion_service.reconcile(
            repository=self.deps.knowledge_repository,
            review_run_id=state.run_id,
            hot_knowledge_items=state.knowledge_items,
        )
        state.metadata['knowledge_promotion'] = promotion_result.model_dump(mode='json')
        state.metadata['promoted_count'] = promotion_result.promoted_count
        state.metadata['demoted_count'] = promotion_result.demoted_count
        state.metadata['archived_count'] = promotion_result.archived_count
        active_cold_rows = self.deps.knowledge_repository.get_active_cold_knowledge(limit=500)
        state.metadata['cold_knowledge_total'] = len(active_cold_rows)
        state.review_verdict.metrics.update(
            {
                'promoted_count': promotion_result.promoted_count,
                'demoted_count': promotion_result.demoted_count,
                'archived_count': promotion_result.archived_count,
                'cold_knowledge_total': len(active_cold_rows),
            }
        )
        state.review_verdict.knowledge_actions = promotion_result.actions
        return state

    def finalize_review(self, state: FlowState) -> FlowState:
        if state.review_verdict is None:
            return state

        report = self.deps.review_repository.create(
            run_id=state.run_id,
            target_run_id=state.review_verdict.target_run_id,
            as_of_date=state.as_of_date,
            horizon=state.review_verdict.horizon,
            summary_text=state.review_verdict.summary_text,
            verdicts_json={'items': [item.model_dump(mode='json') for item in state.review_verdict.verdicts]},
            metrics_json=state.review_verdict.metrics,
            knowledge_json={
                'items': [item.model_dump(mode='json') for item in state.knowledge_items],
                'updated_count': state.metadata.get('hot_knowledge_updated_count', 0),
                'actions': state.review_verdict.knowledge_actions,
                'promoted_count': state.metadata.get('promoted_count', 0),
                'demoted_count': state.metadata.get('demoted_count', 0),
                'archived_count': state.metadata.get('archived_count', 0),
                'cold_knowledge_total': state.metadata.get('cold_knowledge_total', 0),
            },
        )
        state.metadata['review_report_id'] = report.review_report_id
        return state

    def _build_verdict(
        self,
        recommendation: dict,
        outcome: dict,
        horizon: int,
        review_errors: list[dict],
    ) -> RecommendationVerdict:
        expected_action = RecommendationAction(recommendation['action'])
        if outcome.get('status') != 'ok':
            error_json = {
                'recommendation_id': recommendation['recommendation_id'],
                'symbol': recommendation['symbol'],
                'message': outcome.get('error', 'realized outcome is unavailable'),
            }
            review_errors.append(error_json)
            return RecommendationVerdict(
                recommendation_id=recommendation['recommendation_id'],
                symbol=recommendation['symbol'],
                expected_action=expected_action,
                verdict='insufficient_data',
                key_failure_factors=['missing_price_data'],
                evidence_json=recommendation.get('evidence_json', {}),
                error_json=error_json,
            )

        selected_return = (
            outcome.get('actual_return_5d')
            if horizon == 5
            else outcome.get('actual_return_3d')
            if horizon == 3
            else outcome.get('actual_return_1d')
        )
        benchmark_return = outcome.get('benchmark_return')
        max_drawdown = outcome.get('max_drawdown')

        verdict = 'neutral'
        success_factors = []
        failure_factors = []
        if selected_return is None or benchmark_return is None:
            verdict = 'insufficient_data'
            failure_factors.append('missing_horizon_return')
        elif expected_action == RecommendationAction.INCLUDE and selected_return > benchmark_return:
            verdict = 'outperform'
            success_factors.extend(['beat_benchmark', 'include_action_supported'])
            if (max_drawdown or 0.0) >= -0.05:
                success_factors.append('drawdown_controlled')
        elif expected_action == RecommendationAction.EXCLUDE and selected_return <= benchmark_return:
            verdict = 'outperform'
            success_factors.extend(['benchmark_avoidance', 'exclude_action_supported'])
        elif selected_return < benchmark_return:
            verdict = 'underperform'
            failure_factors.extend(['lagged_benchmark', 'signal_follow_through_weak'])
        elif selected_return < 0:
            verdict = 'underperform'
            failure_factors.append('negative_absolute_return')

        if expected_action == RecommendationAction.WATCH and verdict == 'neutral':
            success_factors.append('watch_action_preserved_optional_entry')
        if (max_drawdown or 0.0) < -0.08:
            failure_factors.append('drawdown_exceeded_threshold')

        return RecommendationVerdict(
            recommendation_id=recommendation['recommendation_id'],
            symbol=recommendation['symbol'],
            expected_action=expected_action,
            actual_return_1d=outcome.get('actual_return_1d'),
            actual_return_3d=outcome.get('actual_return_3d'),
            actual_return_5d=outcome.get('actual_return_5d'),
            benchmark_return=benchmark_return,
            max_drawdown=max_drawdown,
            verdict=verdict,
            key_success_factors=success_factors,
            key_failure_factors=failure_factors,
            evidence_json=recommendation.get('evidence_json', {}),
            error_json={},
        )

    def _build_knowledge_item(self, state: FlowState, verdict: RecommendationVerdict) -> KnowledgeItem | None:
        horizon = int(state.metadata.get('review_horizon', 5))
        if verdict.verdict == 'outperform':
            text = f'{verdict.expected_action.value} candidates with evidence support can outperform benchmark over {horizon}d.'
            category = 'review_success_rule'
            pass_count = 1
            fail_count = 0
        elif verdict.verdict == 'underperform':
            text = f'{verdict.expected_action.value} candidates that fail to beat benchmark over {horizon}d need tighter risk control.'
            category = 'review_failure_rule'
            pass_count = 0
            fail_count = 1
        elif verdict.verdict == 'insufficient_data':
            text = f'Recommendations without enough post-signal market data should be tagged as insufficient_data.'
            category = 'review_data_quality_rule'
            pass_count = 0
            fail_count = 1
        else:
            return None

        return KnowledgeItem(
            lineage_id=None,
            tier=KnowledgeTier.HOT,
            text=text,
            category=category,
            source_run_ids=[state.run_id, state.metadata.get('target_run_id', '')],
            source_recommendation_ids=[verdict.recommendation_id],
            tests_survived=1,
            pass_count=pass_count,
            fail_count=fail_count,
            status=KnowledgeStatus.ACTIVE,
            applicable_event_tags=normalize_tags(
                verdict.evidence_json.get('normalized_event_tags')
                or verdict.evidence_json.get('event_tags')
                or []
            ),
            applicable_technical_tags=normalize_tags(verdict.evidence_json.get('technical_pattern_tags', [])),
            applicable_market_regimes=normalize_tags(verdict.evidence_json.get('market_regime_tags', [])),
            negative_match_tags=normalize_tags(verdict.evidence_json.get('risk_pattern_tags', [])),
            evidence_json={
                'review_run_id': state.run_id,
                'target_run_id': state.metadata.get('target_run_id', ''),
                'symbol': verdict.symbol,
                'verdict': verdict.verdict,
                'actual_return_5d': verdict.actual_return_5d,
                'benchmark_return': verdict.benchmark_return,
                'max_drawdown': verdict.max_drawdown,
                'last_validation_passed': pass_count > fail_count,
                'event_tags': normalize_tags(
                    verdict.evidence_json.get('normalized_event_tags')
                    or verdict.evidence_json.get('event_tags')
                    or []
                ),
                'technical_pattern_tags': normalize_tags(verdict.evidence_json.get('technical_pattern_tags', [])),
                'risk_pattern_tags': normalize_tags(verdict.evidence_json.get('risk_pattern_tags', [])),
                'market_regimes': normalize_tags(verdict.evidence_json.get('market_regime_tags', [])) or self._derive_market_regimes(verdict),
            },
        )

    @staticmethod
    def _derive_market_regimes(verdict: RecommendationVerdict) -> list[str]:
        market_regimes: list[str] = []

        benchmark_return = verdict.benchmark_return
        actual_return = verdict.actual_return_5d
        if actual_return is None:
            market_regimes.append('market_regime:range_bound_market')
        elif benchmark_return is not None and actual_return >= benchmark_return:
            market_regimes.append('market_regime:benchmark_uptrend')
        else:
            market_regimes.append('market_regime:benchmark_downtrend')

        if benchmark_return is None:
            market_regimes.append('market_regime:range_bound_market')
        elif benchmark_return >= 0:
            market_regimes.append('market_regime:benchmark_uptrend')
        else:
            market_regimes.append('market_regime:benchmark_downtrend')

        max_drawdown = verdict.max_drawdown
        if max_drawdown is None:
            market_regimes.append('market_regime:range_bound_market')
        elif max_drawdown <= -0.08:
            market_regimes.append('market_regime:high_volatility')
        else:
            market_regimes.append('market_regime:controlled_volatility')

        return list(dict.fromkeys(market_regimes))
