from __future__ import annotations

from datetime import date

from core.enums import FlowType
from domain.schemas import WorkflowTriggerIn
from workflows.service import WorkflowApplicationService


def test_observe_flow_integration(harness):
    service = WorkflowApplicationService(lambda: harness.deps)
    trigger = WorkflowTriggerIn(flow_type=FlowType.OBSERVE, as_of_date=date(2026, 3, 25))
    run = service.trigger_workflow(trigger, async_mode=False)
    assert run.status.value == 'completed'

    stored_run = harness.deps.workflow_runs.get(run.run_id)
    brief = harness.deps.daily_brief_repository.latest_for_date(date(2026, 3, 25))
    snapshots = harness.deps.feature_snapshot_repository.list_by_date(date(2026, 3, 25))
    assert stored_run is not None
    assert stored_run.flow_type == FlowType.OBSERVE
    assert harness.deps.news_repository.count() >= 1
    assert brief is not None
    assert len(snapshots) >= 2
    assert stored_run.output_json.get('daily_brief')
    assert brief.evidence_json.get('normalized_event_tags')
    assert any(
        row.features_json.get('technical_pattern_tags') or row.features_json.get('market_regime_tags')
        for row in snapshots
    )
