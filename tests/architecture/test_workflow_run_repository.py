from __future__ import annotations

from datetime import date

from core.enums import FlowType, RunStatus
from core.ids import generate_prefixed_id


def test_workflow_run_repository_create_and_update(harness):
    repo = harness.deps.workflow_runs
    run = repo.create(
        run_id=generate_prefixed_id('observe'),
        flow_type=FlowType.OBSERVE,
        status=RunStatus.PENDING,
        as_of_date=date(2026, 3, 25),
        trigger_source='test',
        idempotency_key='observe:2026-03-25',
        prompt_version='prompt-v1',
        agent_version='agent-v1',
        feature_set_version='feature-v1',
        model_version='model-v1',
        input_json={},
        output_json={},
        metadata_json={},
        error_json={},
    )
    fetched = repo.get(run.run_id)
    assert fetched is not None
    assert fetched.idempotency_key == 'observe:2026-03-25'

    repo.update(run.run_id, status=RunStatus.COMPLETED)
    updated = repo.get(run.run_id)
    assert updated.status == RunStatus.COMPLETED
    assert repo.get_by_idempotency_key('observe:2026-03-25').run_id == run.run_id
