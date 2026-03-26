from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import ValidationError

from apps.api.deps import get_knowledge_analytics_service, get_workflow_service
from apps.api.responses import ApiResponse
from domain.schemas import KnowledgeAnalyticsWindow

router = APIRouter(prefix='/api/knowledge', tags=['knowledge'])


def _build_window(
    *,
    window_type: str,
    window_value: int | None,
    view_mode: str,
) -> KnowledgeAnalyticsWindow:
    try:
        return KnowledgeAnalyticsWindow(
            window_type=window_type,
            window_value=window_value,
            view_mode=view_mode,
        )
    except ValidationError as exc:
        first_error = exc.errors()[0]
        raise HTTPException(status_code=422, detail=first_error.get('msg', 'invalid knowledge analytics window')) from exc


@router.get('/hot', response_model=ApiResponse)
def list_hot_knowledge(limit: int = Query(default=100, ge=1, le=200)):
    items = get_workflow_service().list_hot_knowledge(limit=limit)
    return ApiResponse(data=items)


@router.get('/coverage', response_model=ApiResponse)
def get_knowledge_coverage(
    limit: int = Query(default=500, ge=1, le=5000),
    window_type: str = Query(default='all_time', pattern='^(all_time|reviews|days)$'),
    window_value: int | None = Query(default=None, ge=1, le=5000),
    view_mode: str = Query(default='active', pattern='^(active|lineage)$'),
):
    window = _build_window(window_type=window_type, window_value=window_value, view_mode=view_mode)
    report = get_knowledge_analytics_service().build_coverage_report(
        limit=limit,
        window_type=window.window_type,
        window_value=window.window_value,
        view_mode=window.view_mode,
    )
    return ApiResponse(data=report)


@router.get('/coverage/trends', response_model=ApiResponse)
def get_knowledge_coverage_trends(
    limit: int = Query(default=500, ge=1, le=5000),
    knowledge_id: str | None = Query(default=None),
    lineage_id: str | None = Query(default=None),
    view_mode: str = Query(default='active', pattern='^(active|lineage)$'),
):
    report = get_knowledge_analytics_service().build_coverage_trends(
        limit=limit,
        knowledge_id=knowledge_id,
        lineage_id=lineage_id,
        view_mode=view_mode,
    )
    return ApiResponse(data=report)


@router.get('/coverage/{knowledge_id}', response_model=ApiResponse)
def get_knowledge_coverage_detail(
    knowledge_id: str,
    limit: int = Query(default=500, ge=1, le=5000),
    window_type: str = Query(default='all_time', pattern='^(all_time|reviews|days)$'),
    window_value: int | None = Query(default=None, ge=1, le=5000),
    view_mode: str = Query(default='active', pattern='^(active|lineage)$'),
):
    window = _build_window(window_type=window_type, window_value=window_value, view_mode=view_mode)
    item = get_knowledge_analytics_service().get_knowledge_coverage(
        knowledge_id=knowledge_id,
        limit=limit,
        window_type=window.window_type,
        window_value=window.window_value,
        view_mode=window.view_mode,
    )
    if item is None:
        raise HTTPException(status_code=404, detail='knowledge not found')
    return ApiResponse(data=item)


@router.get('/pruning/trends', response_model=ApiResponse)
def get_pruning_trends(
    limit: int = Query(default=500, ge=1, le=5000),
    knowledge_id: str | None = Query(default=None),
    lineage_id: str | None = Query(default=None),
    view_mode: str = Query(default='active', pattern='^(active|lineage)$'),
):
    report = get_knowledge_analytics_service().build_pruning_trends(
        limit=limit,
        knowledge_id=knowledge_id,
        lineage_id=lineage_id,
        view_mode=view_mode,
    )
    return ApiResponse(data=report)


@router.get('/pruning-candidates', response_model=ApiResponse)
def get_pruning_candidates(
    limit: int = Query(default=500, ge=1, le=5000),
    window_type: str = Query(default='all_time', pattern='^(all_time|reviews|days)$'),
    window_value: int | None = Query(default=None, ge=1, le=5000),
    view_mode: str = Query(default='active', pattern='^(active|lineage)$'),
):
    window = _build_window(window_type=window_type, window_value=window_value, view_mode=view_mode)
    report = get_knowledge_analytics_service().list_pruning_candidates(
        limit=limit,
        window_type=window.window_type,
        window_value=window.window_value,
        view_mode=window.view_mode,
    )
    return ApiResponse(data=report)


@router.get('/lifecycle-summary', response_model=ApiResponse)
def get_lifecycle_summary(
    limit: int = Query(default=500, ge=1, le=5000),
    category: str | None = Query(default=None),
    regime: str | None = Query(default=None),
):
    report = get_knowledge_analytics_service().build_lifecycle_report(
        limit=limit,
        category=category,
        regime=regime,
    )
    return ApiResponse(data=report)


@router.get('/lineages/{lineage_id}/lifecycle-summary', response_model=ApiResponse)
def get_lineage_lifecycle_summary(
    lineage_id: str,
    limit: int = Query(default=500, ge=1, le=5000),
):
    report = get_knowledge_analytics_service().get_lineage_lifecycle_summary(
        lineage_id=lineage_id,
        limit=limit,
    )
    if report is None:
        raise HTTPException(status_code=404, detail='knowledge lineage not found')
    return ApiResponse(data=report)


@router.get('/lineages/{lineage_id}/timeline', response_model=ApiResponse)
def get_lineage_timeline(
    lineage_id: str,
    limit: int = Query(default=500, ge=1, le=5000),
    descending: bool = Query(default=False),
):
    report = get_knowledge_analytics_service().get_lineage_timeline(
        lineage_id=lineage_id,
        limit=limit,
        descending=descending,
    )
    if report is None:
        raise HTTPException(status_code=404, detail='knowledge lineage not found')
    return ApiResponse(data=report)


@router.get('/{knowledge_id}/timeline', response_model=ApiResponse)
def get_knowledge_timeline(
    knowledge_id: str,
    limit: int = Query(default=500, ge=1, le=5000),
    descending: bool = Query(default=False),
):
    report = get_knowledge_analytics_service().get_knowledge_timeline(
        knowledge_id=knowledge_id,
        limit=limit,
        descending=descending,
    )
    if report is None:
        raise HTTPException(status_code=404, detail='knowledge not found')
    return ApiResponse(data=report)


@router.get('/{knowledge_id}/trends', response_model=ApiResponse)
def get_knowledge_trends(
    knowledge_id: str,
    limit: int = Query(default=500, ge=1, le=5000),
    view_mode: str = Query(default='active', pattern='^(active|lineage)$'),
):
    report = get_knowledge_analytics_service().get_knowledge_trends(
        knowledge_id=knowledge_id,
        limit=limit,
        view_mode=view_mode,
    )
    if report is None:
        raise HTTPException(status_code=404, detail='knowledge not found')
    return ApiResponse(data=report)
