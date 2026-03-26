from __future__ import annotations

from datetime import date

from core.enums import FlowType, KnowledgeStatus, RecommendationAction, RunStatus
from core.ids import generate_prefixed_id
from domain.schemas import KnowledgeItem, WorkflowTriggerIn
from memory.promotion import KnowledgePromotionService
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


def _to_knowledge_item(row) -> KnowledgeItem:
    return KnowledgeItem.model_validate(
        {
            'knowledge_id': row.knowledge_id,
            'text': row.text,
            'category': row.category,
            'source_run_ids': row.source_run_ids,
            'source_recommendation_ids': row.source_recommendation_ids,
            'tests_survived': row.tests_survived,
            'pass_count': row.pass_count,
            'fail_count': row.fail_count,
            'pass_rate': row.pass_rate,
            'status': row.status,
            'evidence_json': row.evidence_json,
        }
    )


def _find_outperform_symbol(harness, as_of_date: date) -> str:
    candidates = ['000001.SZ', '600519.SH', '300750.SZ', '601318.SH', '000858.SZ']
    outcomes = harness.deps.market_data_client.load_realized_outcomes(candidates, as_of_date, horizon=5)
    for symbol, outcome in outcomes.items():
        if outcome.get('status') == 'ok' and outcome.get('actual_return_5d') is not None:
            if outcome['actual_return_5d'] > outcome.get('benchmark_return', 0.0):
                return symbol
    raise AssertionError('expected at least one symbol to outperform the benchmark in stub data')


def test_hot_knowledge_is_promoted_to_cold_when_threshold_met(harness):
    repository = harness.deps.knowledge_repository
    review_run_id = generate_prefixed_id('review')
    _create_workflow_run(harness, review_run_id, FlowType.REVIEW, date(2026, 3, 26))

    hot = repository.create_hot_knowledge(
        {
            'text': 'validated momentum rule',
            'category': 'test_rule',
            'source_run_ids': ['reason_seed'],
            'source_recommendation_ids': ['rec_seed'],
            'tests_survived': 10,
            'pass_count': 7,
            'fail_count': 3,
            'pass_rate': 0.7,
            'status': KnowledgeStatus.ACTIVE,
            'evidence_json': {
                'market_regimes': ['benchmark_uptrend', 'controlled_volatility'],
                'last_validation_passed': True,
            },
        },
        source_run_id=review_run_id,
    )

    result = KnowledgePromotionService().reconcile(
        repository=repository,
        review_run_id=review_run_id,
        hot_knowledge_items=[_to_knowledge_item(hot)],
    )

    cold_rows = repository.get_active_cold_knowledge(limit=10)
    stored_hot = repository.get_hot(hot.knowledge_id)

    assert result.promoted_count == 1
    assert len(cold_rows) == 1
    assert cold_rows[0].source_hot_knowledge_id == hot.knowledge_id
    assert stored_hot.status == KnowledgeStatus.ARCHIVED


def test_promotion_writes_knowledge_events(harness):
    repository = harness.deps.knowledge_repository
    review_run_id = generate_prefixed_id('review')
    _create_workflow_run(harness, review_run_id, FlowType.REVIEW, date(2026, 3, 26))

    hot = repository.create_hot_knowledge(
        {
            'text': 'validated reversal rule',
            'category': 'test_rule',
            'source_run_ids': ['reason_seed'],
            'source_recommendation_ids': ['rec_seed'],
            'tests_survived': 12,
            'pass_count': 8,
            'fail_count': 4,
            'pass_rate': 0.6667,
            'status': KnowledgeStatus.ACTIVE,
            'evidence_json': {
                'market_regimes': ['benchmark_downtrend', 'high_volatility'],
                'last_validation_passed': True,
            },
        },
        source_run_id=review_run_id,
    )

    KnowledgePromotionService().reconcile(
        repository=repository,
        review_run_id=review_run_id,
        hot_knowledge_items=[_to_knowledge_item(hot)],
    )
    events = repository.list_knowledge_events(limit=20)
    event_types = {(event.knowledge_id, event.event_type) for event in events}

    assert (hot.knowledge_id, 'promoted_to_cold') in event_types
    assert any(event_type == 'promoted_from_hot' for _, event_type in event_types)


def test_hot_knowledge_is_not_promoted_when_threshold_not_met(harness):
    repository = harness.deps.knowledge_repository
    review_run_id = generate_prefixed_id('review')
    _create_workflow_run(harness, review_run_id, FlowType.REVIEW, date(2026, 3, 26))

    hot = repository.create_hot_knowledge(
        {
            'text': 'insufficient validation rule',
            'category': 'test_rule',
            'source_run_ids': ['reason_seed'],
            'source_recommendation_ids': ['rec_seed'],
            'tests_survived': 9,
            'pass_count': 6,
            'fail_count': 3,
            'pass_rate': 0.6667,
            'status': KnowledgeStatus.ACTIVE,
            'evidence_json': {
                'market_regimes': ['benchmark_uptrend'],
                'last_validation_passed': True,
            },
        },
        source_run_id=review_run_id,
    )

    result = KnowledgePromotionService().reconcile(
        repository=repository,
        review_run_id=review_run_id,
        hot_knowledge_items=[_to_knowledge_item(hot)],
    )

    assert result.promoted_count == 0
    assert repository.get_active_cold_knowledge(limit=10) == []


def test_cold_knowledge_is_demoted_after_consecutive_failures(harness):
    repository = harness.deps.knowledge_repository
    promotion_run_id = generate_prefixed_id('review')
    _create_workflow_run(harness, promotion_run_id, FlowType.REVIEW, date(2026, 3, 26))

    hot = repository.create_hot_knowledge(
        {
            'text': 'fragile breakout rule',
            'category': 'test_rule',
            'source_run_ids': ['reason_seed'],
            'source_recommendation_ids': ['rec_seed'],
            'tests_survived': 10,
            'pass_count': 7,
            'fail_count': 3,
            'pass_rate': 0.7,
            'status': KnowledgeStatus.ACTIVE,
            'evidence_json': {
                'market_regimes': ['benchmark_uptrend', 'controlled_volatility'],
                'last_validation_passed': True,
            },
        },
        source_run_id=promotion_run_id,
    )
    promotion_result = KnowledgePromotionService().reconcile(
        repository=repository,
        review_run_id=promotion_run_id,
        hot_knowledge_items=[_to_knowledge_item(hot)],
    )
    assert promotion_result.promoted_count == 1

    final_result = None
    for _ in range(3):
        fail_run_id = generate_prefixed_id('review')
        _create_workflow_run(harness, fail_run_id, FlowType.REVIEW, date(2026, 3, 27))
        repository.update_hot_knowledge_stats(
            hot.knowledge_id,
            item={
                'tests_survived': 1,
                'pass_count': 0,
                'fail_count': 1,
                'status': KnowledgeStatus.ARCHIVED,
                'evidence_json': {
                    'market_regimes': ['benchmark_downtrend', 'high_volatility'],
                    'last_validation_passed': False,
                },
            },
            source_run_id=fail_run_id,
        )
        final_result = KnowledgePromotionService().reconcile(
            repository=repository,
            review_run_id=fail_run_id,
            hot_knowledge_items=[_to_knowledge_item(repository.get_hot(hot.knowledge_id))],
        )

    cold_rows = repository.get_active_cold_knowledge(limit=10)
    stored_hot = repository.get_hot(hot.knowledge_id)
    events = repository.list_knowledge_events(limit=50)

    assert final_result is not None
    assert final_result.demoted_count == 1
    assert cold_rows == []
    assert stored_hot.status == KnowledgeStatus.DEGRADED
    assert any(event.event_type == 'demoted_to_hot' for event in events)


def test_review_flow_metrics_include_promotion_and_demotion_counts(harness):
    service = WorkflowApplicationService(lambda: harness.deps)
    target_run_id = generate_prefixed_id('reason')
    _create_workflow_run(harness, target_run_id, FlowType.REASON, date(2026, 3, 25))

    symbol = _find_outperform_symbol(harness, date(2026, 3, 25))
    harness.deps.recommendation_repository.bulk_create(
        [
            {
                'run_id': target_run_id,
                'prediction_artifact_id': None,
                'symbol': symbol,
                'action': RecommendationAction.INCLUDE,
                'weight': 0.8,
                'final_score': 0.82,
                'reason': 'promotion seed',
                'risk_flags_json': {'risk_flags': []},
                'evidence_json': {
                    'evidence_refs': [{'ref_id': 'seed_ref', 'ref_type': 'manual_seed', 'title': 'seed'}]
                },
            }
        ]
    )
    harness.deps.knowledge_repository.create_hot_knowledge(
        {
            'text': 'include candidates with evidence support can outperform benchmark over 5d.',
            'category': 'review_success_rule',
            'source_run_ids': [target_run_id],
            'source_recommendation_ids': ['seed_recommendation'],
            'tests_survived': 9,
            'pass_count': 6,
            'fail_count': 3,
            'pass_rate': 0.6667,
            'status': KnowledgeStatus.ACTIVE,
            'evidence_json': {
                'market_regimes': ['benchmark_uptrend', 'controlled_volatility'],
                'last_validation_passed': True,
            },
        },
        source_run_id=target_run_id,
    )

    review_run = service.trigger_workflow(
        WorkflowTriggerIn(
            flow_type=FlowType.REVIEW,
            as_of_date=date(2026, 3, 26),
            payload={'target_run_id': target_run_id, 'horizon': 5},
        ),
        async_mode=False,
    )

    report = harness.deps.review_repository.get_by_run(review_run.run_id)
    cold_rows = harness.deps.knowledge_repository.get_active_cold_knowledge(limit=10)

    assert report is not None
    assert report.metrics_json['promoted_count'] == 1
    assert report.metrics_json['demoted_count'] == 0
    assert 'archived_count' in report.metrics_json
    assert cold_rows
