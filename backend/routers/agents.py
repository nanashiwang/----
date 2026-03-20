from fastapi import APIRouter, Depends, HTTPException
from typing import List

from ..models.settings import AgentConfigOut, AgentConfigUpdate
from ..auth.dependencies import get_current_user, require_admin
from ..services.settings_service import AgentConfigService

router = APIRouter(prefix="/api/agents", tags=["Agent管理"])


def _get_service():
    from ..app import get_sqlite_client
    return AgentConfigService(get_sqlite_client())


@router.get("", response_model=List[AgentConfigOut])
async def list_agents(_=Depends(get_current_user)):
    svc = _get_service()
    rows = svc.list_all()
    return [AgentConfigOut(**r) for r in rows]


@router.get("/{agent_id}", response_model=AgentConfigOut)
async def get_agent(agent_id: int, _=Depends(get_current_user)):
    svc = _get_service()
    row = svc.get_by_id(agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent不存在")
    return AgentConfigOut(**row)


@router.put("/{agent_id}", response_model=AgentConfigOut)
async def update_agent(agent_id: int, data: AgentConfigUpdate, _=Depends(require_admin)):
    svc = _get_service()
    if not svc.get_by_id(agent_id):
        raise HTTPException(status_code=404, detail="Agent不存在")
    try:
        svc.update(agent_id, data.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = svc.get_by_id(agent_id)
    return AgentConfigOut(**row)
