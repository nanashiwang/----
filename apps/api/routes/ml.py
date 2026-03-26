from __future__ import annotations

from fastapi import APIRouter

from apps.api.deps import get_ml_service
from apps.api.responses import ApiResponse
from domain.schemas import MLExperimentRequest

router = APIRouter(prefix='/api/ml', tags=['ml'])


@router.post('/experiments/run', response_model=ApiResponse)
def run_ml_experiment(payload: MLExperimentRequest):
    result = get_ml_service().run(payload)
    return ApiResponse(data=result)
