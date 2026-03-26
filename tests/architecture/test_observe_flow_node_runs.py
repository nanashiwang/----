from __future__ import annotations

from datetime import date

from core.enums import FlowType
from domain.schemas import WorkflowTriggerIn
from workflows.service import WorkflowApplicationService


def test_observe_flow_writes_agent_node_runs(harness):
    service = WorkflowApplicationService(lambda: harness.deps)
    run = service.trigger_workflow(
        WorkflowTriggerIn(flow_type=FlowType.OBSERVE, as_of_date=date(2026, 3, 25)),
        async_mode=False,
    )

    node_runs = harness.deps.agent_node_runs.list_by_run(run.run_id)

    assert len(node_runs) == 6
    assert [item.node_name for item in node_runs] == [
        'ingest_news_articles',
        'build_daily_brief',
        'load_watchlist_symbols',
        'build_market_snapshot',
        'build_indicator_snapshot',
        'finalize_observe',
    ]
    assert all(item.error_json == {} for item in node_runs)
