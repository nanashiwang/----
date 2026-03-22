from fastapi import APIRouter, Depends, Query

from ..auth.dependencies import require_admin
from ..models.admin_log import AdminUsageLogListOut
from ..services.usage_log_service import UsageLogService

router = APIRouter(prefix="/api/admin/logs", tags=["管理日志"])


def _get_service() -> UsageLogService:
    from ..app import get_sqlite_client

    return UsageLogService(get_sqlite_client())


@router.get("", response_model=AdminUsageLogListOut)
async def list_admin_logs(
    limit: int = Query(default=100, ge=1, le=200),
    module: str = "",
    username: str = "",
    method: str = "",
    status: str = Query(default="", pattern="^(|success|failed)$"),
    _=Depends(require_admin),
):
    return AdminUsageLogListOut(
        **_get_service().list_logs(
            limit=limit,
            module=module,
            username=username,
            method=method,
            status=status,
        )
    )

