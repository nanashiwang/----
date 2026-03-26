from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from apps.api.app import create_app
from core.enums import FlowType
from domain.schemas import WorkflowTriggerIn
from workflows.service import WorkflowApplicationService


def test_workflow_query_routes_return_run_logs_and_recommendations(harness, monkeypatch):
    service = WorkflowApplicationService(lambda: harness.deps)
    trade_date = date(2026, 3, 25)

    service.trigger_workflow(
        WorkflowTriggerIn(flow_type=FlowType.OBSERVE, as_of_date=trade_date),
        async_mode=False,
    )
    reason_run = service.trigger_workflow(
        WorkflowTriggerIn(flow_type=FlowType.REASON, as_of_date=trade_date),
        async_mode=False,
    )
    review_run = service.trigger_workflow(
        WorkflowTriggerIn(
            flow_type=FlowType.REVIEW,
            as_of_date=date(2026, 3, 26),
            payload={'target_run_id': reason_run.run_id, 'horizon': 5},
        ),
        async_mode=False,
    )

    monkeypatch.setattr("apps.api.routes.workflow.get_workflow_service", lambda: service)
    monkeypatch.setattr("apps.api.routes.knowledge.get_workflow_service", lambda: service)
    client = TestClient(create_app())

    run_response = client.get(f"/api/workflow/runs/{reason_run.run_id}")
    assert run_response.status_code == 200
    assert run_response.json()["data"]["run_id"] == reason_run.run_id

    log_response = client.get(f"/api/workflow/runs/{reason_run.run_id}/logs")
    assert log_response.status_code == 200
    assert len(log_response.json()["data"]) == 10

    rec_response = client.get(f"/api/workflow/runs/{reason_run.run_id}/recommendations")
    assert rec_response.status_code == 200
    assert rec_response.json()["data"]

    report_response = client.get(f"/api/workflow/runs/{review_run.run_id}/review-report")
    assert report_response.status_code == 200
    assert report_response.json()["data"]["run_id"] == review_run.run_id

    knowledge_response = client.get("/api/knowledge/hot")
    assert knowledge_response.status_code == 200
    assert knowledge_response.json()["data"]


def test_workflow_query_routes_return_standard_error_when_run_missing(harness, monkeypatch):
    service = WorkflowApplicationService(lambda: harness.deps)
    monkeypatch.setattr("apps.api.routes.workflow.get_workflow_service", lambda: service)
    client = TestClient(create_app())

    response = client.get("/api/workflow/runs/run_missing/recommendations")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "workflow run not found"


def test_review_trigger_returns_standard_error_when_target_run_missing(harness, monkeypatch):
    service = WorkflowApplicationService(lambda: harness.deps)
    monkeypatch.setattr("apps.api.routes.workflow.get_workflow_service", lambda: service)
    client = TestClient(create_app())

    response = client.post(
        "/api/workflow/review",
        json={
            "as_of_date": "2026-03-26",
            "payload": {"target_run_id": "run_missing", "horizon": 5},
        },
    )

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "target_run_id not found"
