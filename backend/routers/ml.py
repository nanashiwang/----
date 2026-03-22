from fastapi import APIRouter, Depends
from loguru import logger

from ..auth.dependencies import get_current_user
from ..models.ml import MlExperimentOptionsOut, MlExperimentRequest, MlExperimentResultOut
from ..services.ml_service import MLExperimentService
from ..services.usage_log_service import UsageLogService

router = APIRouter(prefix="/api/ml", tags=["机器学习实验"])


def _get_service() -> MLExperimentService:
    from ..app import get_sqlite_client

    return MLExperimentService(get_sqlite_client())


@router.get("/options", response_model=MlExperimentOptionsOut)
async def get_ml_options(_=Depends(get_current_user)):
    return MlExperimentOptionsOut(**_get_service().get_options())


@router.post("/experiments/run", response_model=MlExperimentResultOut)
async def run_ml_experiment(
    payload: MlExperimentRequest,
    current_user=Depends(get_current_user),
):
    try:
        result = _get_service().run_experiment(payload)
        try:
            _get_usage_log_service().record_ml_experiment(current_user, payload, result)
        except Exception as exc:  # pragma: no cover - 日志失败不应中断主流程
            logger.warning("记录机器学习实验日志失败: {}", exc)
        return MlExperimentResultOut(**result)
    except ValueError as exc:
        error_result = MlExperimentResultOut(
            error=str(exc),
            params=payload.model_dump(),
        )
        try:
            _get_usage_log_service().record_ml_experiment(current_user, payload, error_result.model_dump())
        except Exception as log_exc:  # pragma: no cover - 日志失败不应中断主流程
            logger.warning("记录机器学习实验失败日志失败: {}", log_exc)
        return error_result


def _get_usage_log_service() -> UsageLogService:
    from ..app import get_sqlite_client

    return UsageLogService(get_sqlite_client())
