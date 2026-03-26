from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.deps import get_workflow_service
from apps.api.responses import ApiResponse
from core.enums import FlowType
from domain.schemas import RecommendationRecordOut, ReviewReportOut, WorkflowLogOut, WorkflowTriggerIn

router = APIRouter(prefix='/api/workflow', tags=['workflow'])


def _ensure_flow(payload: WorkflowTriggerIn, flow_type: FlowType) -> WorkflowTriggerIn:
    payload_dict = payload.model_dump(mode='json')
    payload_dict['flow_type'] = flow_type
    return WorkflowTriggerIn.model_validate(payload_dict)


def _get_existing_run_or_404(run_id: str):
    run = get_workflow_service().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail='workflow run not found')
    return run


def _ensure_review_target_exists(payload: WorkflowTriggerIn) -> None:
    target_run_id = payload.payload.get('target_run_id') or payload.payload.get('recommendation_run_id')
    if not target_run_id:
        raise HTTPException(status_code=400, detail='target_run_id is required for review flow')
    if get_workflow_service().get_run(target_run_id) is None:
        raise HTTPException(status_code=404, detail='target_run_id not found')


@router.post('/observe', response_model=ApiResponse)
def trigger_observe(payload: WorkflowTriggerIn):
    run = get_workflow_service().trigger_workflow(_ensure_flow(payload, FlowType.OBSERVE), async_mode=True)
    return ApiResponse(data=run)


@router.post('/reason', response_model=ApiResponse)
def trigger_reason(payload: WorkflowTriggerIn):
    run = get_workflow_service().trigger_workflow(_ensure_flow(payload, FlowType.REASON), async_mode=True)
    return ApiResponse(data=run)


@router.post('/review', response_model=ApiResponse)
def trigger_review(payload: WorkflowTriggerIn):
    _ensure_review_target_exists(payload)
    run = get_workflow_service().trigger_workflow(_ensure_flow(payload, FlowType.REVIEW), async_mode=True)
    return ApiResponse(data=run)


@router.get('/runs/{run_id}', response_model=ApiResponse)
def get_workflow_run(run_id: str):
    run = _get_existing_run_or_404(run_id)
    return ApiResponse(data=run)


@router.get('/runs/{run_id}/logs', response_model=ApiResponse)
def get_workflow_logs(run_id: str):
    _get_existing_run_or_404(run_id)
    logs = [WorkflowLogOut.model_validate(item) for item in get_workflow_service().get_run_logs(run_id)]
    return ApiResponse(data=logs)


@router.get('/runs/{run_id}/recommendations', response_model=ApiResponse)
def get_workflow_recommendations(run_id: str):
    _get_existing_run_or_404(run_id)
    recommendations = [
        RecommendationRecordOut.model_validate(item)
        for item in get_workflow_service().get_run_recommendations(run_id)
    ]
    return ApiResponse(data=recommendations)


@router.get('/runs/{run_id}/review-report', response_model=ApiResponse)
def get_workflow_review_report(run_id: str):
    _get_existing_run_or_404(run_id)
    report = get_workflow_service().get_review_report(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail='review report not found')
    return ApiResponse(data=ReviewReportOut.model_validate(report))
