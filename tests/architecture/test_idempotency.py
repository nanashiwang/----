from __future__ import annotations

from datetime import date

from core.enums import FlowType
from domain.schemas import WorkflowTriggerIn
from workflows.service import WorkflowApplicationService


def test_observe_flow_idempotency_returns_same_run(harness):
    service = WorkflowApplicationService(lambda: harness.deps)
    trigger = WorkflowTriggerIn(flow_type=FlowType.OBSERVE, as_of_date=date(2026, 3, 25))
    first = service.trigger_workflow(trigger, async_mode=True)
    second = service.trigger_workflow(trigger, async_mode=True)
    assert first.run_id == second.run_id
