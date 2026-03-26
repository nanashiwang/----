from __future__ import annotations

from datetime import date

from core.enums import FlowType, RecommendationAction, RunStatus
from core.ids import generate_prefixed_id
from domain.schemas import WorkflowTriggerIn
from workflows.service import WorkflowApplicationService


def _prepare_reason_run(harness, trade_date: date = date(2026, 3, 25)):
    service = WorkflowApplicationService(lambda: harness.deps)
    service.trigger_workflow(
        WorkflowTriggerIn(flow_type=FlowType.OBSERVE, as_of_date=trade_date),
        async_mode=False,
    )
    reason_run = service.trigger_workflow(
        WorkflowTriggerIn(flow_type=FlowType.REASON, as_of_date=trade_date),
        async_mode=False,
    )
    return service, reason_run


def test_review_flow_writes_workflow_run(harness):
    service, reason_run = _prepare_reason_run(harness)

    review_run = service.trigger_workflow(
        WorkflowTriggerIn(
            flow_type=FlowType.REVIEW,
            as_of_date=date(2026, 3, 26),
            payload={'target_run_id': reason_run.run_id, 'horizon': 5},
        ),
        async_mode=False,
    )

    stored_run = harness.deps.workflow_runs.get(review_run.run_id)
    assert stored_run is not None
    assert stored_run.flow_type == FlowType.REVIEW
    assert stored_run.status == RunStatus.COMPLETED


def test_review_flow_writes_agent_node_runs(harness):
    service, reason_run = _prepare_reason_run(harness)

    review_run = service.trigger_workflow(
        WorkflowTriggerIn(
            flow_type=FlowType.REVIEW,
            as_of_date=date(2026, 3, 26),
            payload={'target_run_id': reason_run.run_id, 'horizon': 5},
        ),
        async_mode=False,
    )

    node_runs = harness.deps.agent_node_runs.list_by_run(review_run.run_id)
    assert [item.node_name for item in node_runs] == [
        'load_prior_recommendations',
        'load_realized_outcomes',
        'compare_prediction_vs_outcome',
        'generate_review_brief',
        'update_hot_knowledge',
        'promote_or_demote_knowledge',
        'finalize_review',
    ]


def test_review_flow_generates_review_report(harness):
    service, reason_run = _prepare_reason_run(harness)

    review_run = service.trigger_workflow(
        WorkflowTriggerIn(
            flow_type=FlowType.REVIEW,
            as_of_date=date(2026, 3, 26),
            payload={'target_run_id': reason_run.run_id, 'horizon': 5},
        ),
        async_mode=False,
    )

    report = harness.deps.review_repository.get_by_run(review_run.run_id)

    assert report is not None
    assert report.target_run_id == reason_run.run_id
    assert report.horizon == 5
    assert report.summary_text
    assert report.verdicts_json['items']
    assert 'promoted_count' in report.metrics_json
    assert 'demoted_count' in report.metrics_json


def test_review_flow_marks_insufficient_data_when_outcome_missing(harness):
    service = WorkflowApplicationService(lambda: harness.deps)
    target_run_id = generate_prefixed_id('reason')
    harness.deps.workflow_runs.create(
        run_id=target_run_id,
        flow_type=FlowType.REASON,
        status=RunStatus.COMPLETED,
        as_of_date=date(2026, 3, 25),
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
    harness.deps.recommendation_repository.bulk_create([
        {
            'run_id': target_run_id,
            'prediction_artifact_id': None,
            'symbol': 'MISSING.SH',
            'action': RecommendationAction.INCLUDE,
            'weight': 0.8,
            'final_score': 0.8,
            'reason': 'missing outcome test',
            'risk_flags_json': {'risk_flags': []},
            'evidence_json': {'evidence_refs': [{'ref_id': 'e1', 'ref_type': 'test'}]},
        }
    ])

    review_run = service.trigger_workflow(
        WorkflowTriggerIn(
            flow_type=FlowType.REVIEW,
            as_of_date=date(2026, 3, 26),
            payload={'target_run_id': target_run_id, 'horizon': 5},
        ),
        async_mode=False,
    )

    report = harness.deps.review_repository.get_by_run(review_run.run_id)
    verdict = report.verdicts_json['items'][0]
    stored_run = harness.deps.workflow_runs.get(review_run.run_id)

    assert verdict['verdict'] == 'insufficient_data'
    assert stored_run.error_json.get('errors')
    assert report.metrics_json['promoted_count'] == 0
    assert report.metrics_json['demoted_count'] == 0


def test_hot_knowledge_is_written_and_updated(harness):
    service, reason_run = _prepare_reason_run(harness)

    first_review = service.trigger_workflow(
        WorkflowTriggerIn(
            flow_type=FlowType.REVIEW,
            as_of_date=date(2026, 3, 26),
            payload={'target_run_id': reason_run.run_id, 'horizon': 5},
        ),
        async_mode=False,
    )
    first_items = harness.deps.knowledge_repository.list_hot()

    second_review = service.trigger_workflow(
        WorkflowTriggerIn(
            flow_type=FlowType.REVIEW,
            as_of_date=date(2026, 3, 27),
            payload={'target_run_id': reason_run.run_id, 'horizon': 5},
        ),
        async_mode=False,
    )
    second_items = harness.deps.knowledge_repository.list_hot()

    assert first_review.run_id != second_review.run_id
    assert first_items
    assert second_items
    assert len(second_items) == len(first_items)
    assert any(item.tests_survived >= 2 for item in second_items)
