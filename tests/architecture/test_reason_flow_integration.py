from __future__ import annotations

from datetime import date

from core.enums import FlowType, RecommendationAction, RunStatus
from core.ids import generate_prefixed_id
from domain.schemas import WorkflowTriggerIn
from workflows.service import WorkflowApplicationService


def _create_workflow_run(harness, run_id: str, flow_type: FlowType, as_of_date: date) -> None:
    harness.deps.workflow_runs.create(
        run_id=run_id,
        flow_type=flow_type,
        status=RunStatus.COMPLETED,
        as_of_date=as_of_date,
        trigger_source='test',
        idempotency_key=None,
        prompt_version='prompt-v1',
        agent_version='agent-v1',
        feature_set_version='feature-set-v1',
        model_version='model-v1',
        input_json={},
        output_json={},
        metadata_json={},
        error_json={},
    )


def _prepare_observe(service: WorkflowApplicationService, trade_date: date):
    return service.trigger_workflow(
        WorkflowTriggerIn(flow_type=FlowType.OBSERVE, as_of_date=trade_date),
        async_mode=False,
    )


def _run_reason(service: WorkflowApplicationService, trade_date: date):
    return service.trigger_workflow(
        WorkflowTriggerIn(flow_type=FlowType.REASON, as_of_date=trade_date),
        async_mode=False,
    )


def _seed_cold_knowledge(
    harness,
    *,
    text: str,
    category: str,
    applicable_market_regimes: list[str],
    applicable_event_tags: list[str] | None = None,
    applicable_technical_tags: list[str] | None = None,
    negative_match_tags: list[str] | None = None,
    pass_rate: float = 0.75,
    tests_survived: int = 12,
    pass_count: int = 9,
    fail_count: int = 3,
):
    promotion_run_id = generate_prefixed_id('review')
    _create_workflow_run(harness, promotion_run_id, FlowType.REVIEW, date(2026, 3, 26))
    hot = harness.deps.knowledge_repository.create_hot_knowledge(
        {
            'text': text,
            'category': category,
            'source_run_ids': ['reason_seed'],
            'source_recommendation_ids': ['rec_seed'],
            'tests_survived': tests_survived,
            'pass_count': pass_count,
            'fail_count': fail_count,
            'pass_rate': pass_rate,
            'status': 'active',
            'applicable_event_tags': applicable_event_tags or [],
            'applicable_technical_tags': applicable_technical_tags or [],
            'applicable_market_regimes': applicable_market_regimes,
            'negative_match_tags': negative_match_tags or [],
            'evidence_json': {
                'market_regimes': applicable_market_regimes,
                'event_tags': applicable_event_tags or [],
                'technical_pattern_tags': applicable_technical_tags or [],
                'risk_pattern_tags': negative_match_tags or [],
                'last_validation_passed': True,
            },
        },
        source_run_id=promotion_run_id,
    )
    return harness.deps.knowledge_repository.promote_to_cold(
        knowledge_id=hot.knowledge_id,
        promotion_reason='reason-flow integration seed',
        promotion_run_id=promotion_run_id,
    )


def _recommendation_map(harness, run_id: str):
    return {item.symbol: item for item in harness.deps.recommendation_repository.list_by_run(run_id)}


def test_reason_flow_persists_recommendations(harness):
    service = WorkflowApplicationService(lambda: harness.deps)
    trade_date = date(2026, 3, 25)

    _prepare_observe(service, trade_date)
    reason_run = _run_reason(service, trade_date)

    stored_run = harness.deps.workflow_runs.get(reason_run.run_id)
    recommendations = harness.deps.recommendation_repository.list_by_run(reason_run.run_id)

    assert stored_run is not None
    assert stored_run.flow_type == FlowType.REASON
    assert stored_run.status.value == 'completed'
    assert recommendations
    assert all(item.evidence_json.get('evidence_refs') for item in recommendations)
    assert all(
        item.action != RecommendationAction.INCLUDE or item.evidence_json.get('evidence_refs')
        for item in recommendations
    )


def test_reason_flow_final_score_changes_when_cold_knowledge_matches(harness):
    service = WorkflowApplicationService(lambda: harness.deps)
    trade_date = date(2026, 3, 25)

    _prepare_observe(service, trade_date)
    baseline_run = _run_reason(service, trade_date)
    baseline_recommendations = _recommendation_map(harness, baseline_run.run_id)

    _seed_cold_knowledge(
        harness,
        text='Evidence-backed candidates can outperform in uptrend with controlled volatility.',
        category='review_success_rule',
        applicable_market_regimes=['benchmark_uptrend', 'controlled_volatility'],
        applicable_event_tags=['sector_rotation', 'bullish'],
        applicable_technical_tags=['short_term_uptrend', 'momentum_balanced'],
    )
    adjusted_run = _run_reason(service, trade_date)
    adjusted_recommendations = _recommendation_map(harness, adjusted_run.run_id)
    stored_run = harness.deps.workflow_runs.get(adjusted_run.run_id)

    assert adjusted_recommendations['000001.SZ'].final_score > baseline_recommendations['000001.SZ'].final_score
    assert stored_run.output_json['metadata']['matched_cold_knowledge_count'] >= 1
    assert stored_run.output_json['metadata']['knowledge_adjusted_recommendation_count'] >= 1


def test_risk_cold_knowledge_downgrades_include_recommendation(harness):
    service = WorkflowApplicationService(lambda: harness.deps)
    trade_date = date(2026, 3, 25)

    _prepare_observe(service, trade_date)
    _seed_cold_knowledge(
        harness,
        text='Evidence-backed candidates can outperform in uptrend with controlled volatility.',
        category='review_success_rule',
        applicable_market_regimes=['benchmark_uptrend', 'controlled_volatility'],
        applicable_event_tags=['sector_rotation', 'bullish'],
        applicable_technical_tags=['short_term_uptrend', 'momentum_balanced'],
    )
    include_run = _run_reason(service, trade_date)
    include_recommendations = _recommendation_map(harness, include_run.run_id)
    assert include_recommendations['000001.SZ'].action == RecommendationAction.INCLUDE

    _seed_cold_knowledge(
        harness,
        text='Uptrend setups still require strict risk control when cold knowledge detects fragile follow-through.',
        category='review_failure_rule',
        applicable_market_regimes=['benchmark_uptrend', 'controlled_volatility'],
        applicable_event_tags=['sector_rotation', 'bullish'],
        applicable_technical_tags=['short_term_uptrend', 'momentum_balanced'],
        negative_match_tags=['momentum_balanced', 'event_conflict_risk'],
        pass_rate=0.9,
        tests_survived=15,
        pass_count=13,
        fail_count=2,
    )
    risk_run = _run_reason(service, trade_date)
    risk_recommendations = _recommendation_map(harness, risk_run.run_id)

    assert risk_recommendations['000001.SZ'].action in {RecommendationAction.WATCH, RecommendationAction.EXCLUDE}
    assert 'knowledge_high_risk' in risk_recommendations['000001.SZ'].risk_flags_json['risk_flags']


def test_recommendation_persists_knowledge_refs_and_impact_json(harness):
    service = WorkflowApplicationService(lambda: harness.deps)
    trade_date = date(2026, 3, 25)

    _prepare_observe(service, trade_date)
    _seed_cold_knowledge(
        harness,
        text='Evidence-backed candidates can outperform in uptrend with controlled volatility.',
        category='review_success_rule',
        applicable_market_regimes=['benchmark_uptrend', 'controlled_volatility'],
        applicable_event_tags=['sector_rotation', 'bullish'],
        applicable_technical_tags=['short_term_uptrend', 'momentum_balanced'],
    )
    reason_run = _run_reason(service, trade_date)
    recommendation = _recommendation_map(harness, reason_run.run_id)['000001.SZ']

    assert recommendation.evidence_json['knowledge_refs']
    assert recommendation.evidence_json['knowledge_impact_json']
    assert recommendation.evidence_json['knowledge_match_score'] > 0
    assert recommendation.evidence_json['knowledge_risk_penalty'] >= 0


def test_reason_flow_runs_normally_without_cold_knowledge_match(harness):
    service = WorkflowApplicationService(lambda: harness.deps)
    trade_date = date(2026, 3, 25)

    _prepare_observe(service, trade_date)
    _seed_cold_knowledge(
        harness,
        text='This knowledge is for a regime that is not present in the current sample.',
        category='review_success_rule',
        applicable_market_regimes=['sideways_market', 'event_drought'],
    )
    reason_run = _run_reason(service, trade_date)
    stored_run = harness.deps.workflow_runs.get(reason_run.run_id)
    recommendations = harness.deps.recommendation_repository.list_by_run(reason_run.run_id)

    assert stored_run.status == RunStatus.COMPLETED
    assert stored_run.output_json['metadata']['matched_cold_knowledge_count'] == 0
    assert recommendations
    assert all(not item.evidence_json.get('knowledge_refs') for item in recommendations)


def test_review_flow_reads_recommendation_knowledge_fields(harness):
    service = WorkflowApplicationService(lambda: harness.deps)
    trade_date = date(2026, 3, 25)

    _prepare_observe(service, trade_date)
    _seed_cold_knowledge(
        harness,
        text='Evidence-backed candidates can outperform in uptrend with controlled volatility.',
        category='review_success_rule',
        applicable_market_regimes=['benchmark_uptrend', 'controlled_volatility'],
        applicable_event_tags=['sector_rotation', 'bullish'],
        applicable_technical_tags=['short_term_uptrend', 'momentum_balanced'],
    )
    reason_run = _run_reason(service, trade_date)
    review_run = service.trigger_workflow(
        WorkflowTriggerIn(
            flow_type=FlowType.REVIEW,
            as_of_date=date(2026, 3, 26),
            payload={'target_run_id': reason_run.run_id, 'horizon': 5},
        ),
        async_mode=False,
    )

    report = harness.deps.review_repository.get_by_run(review_run.run_id)
    verdicts = report.verdicts_json['items']

    assert report is not None
    assert any(item['evidence_json'].get('knowledge_refs') for item in verdicts)
    assert any(item['evidence_json'].get('knowledge_impact_json') for item in verdicts)


def test_conflicting_tags_trigger_knowledge_conflict_flag(harness):
    service = WorkflowApplicationService(lambda: harness.deps)
    trade_date = date(2026, 3, 25)

    _prepare_observe(service, trade_date)
    _seed_cold_knowledge(
        harness,
        text='Supportive knowledge for uptrend breakout setups.',
        category='review_success_rule',
        applicable_market_regimes=['benchmark_uptrend', 'controlled_volatility'],
        applicable_event_tags=['sector_rotation', 'bullish'],
        applicable_technical_tags=['short_term_uptrend', 'momentum_balanced'],
        negative_match_tags=['momentum_balanced'],
    )
    reason_run = _run_reason(service, trade_date)
    recommendation = _recommendation_map(harness, reason_run.run_id)['000001.SZ']

    assert recommendation.evidence_json['knowledge_conflict_flag'] is True
    assert any(
        impact['conflicting_tags']
        for impact in recommendation.evidence_json['knowledge_impact_json']
    )
