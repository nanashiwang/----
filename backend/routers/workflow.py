from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from datetime import datetime
import asyncio

from ..auth.dependencies import get_current_user
from ..services.workflow_service import WorkflowRunner

router = APIRouter(prefix="/api/workflow", tags=["工作流"])


@router.post("/observe")
async def run_observe(date: str = None, _=Depends(get_current_user)):
    date = date or datetime.now().strftime("%Y-%m-%d")
    wid = WorkflowRunner.run_observe(date)
    return {"workflow_id": wid, "status": "started"}


@router.post("/reason")
async def run_reason(date: str = None, _=Depends(get_current_user)):
    date = date or datetime.now().strftime("%Y-%m-%d")
    wid = WorkflowRunner.run_reason(date)
    return {"workflow_id": wid, "status": "started"}


@router.post("/review")
async def run_review(date: str = None, _=Depends(get_current_user)):
    from datetime import timedelta
    date = date or (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    wid = WorkflowRunner.run_review(date)
    return {"workflow_id": wid, "status": "started"}


@router.get("/status")
async def get_status(workflow_id: str, _=Depends(get_current_user)):
    s = WorkflowRunner.get_status(workflow_id)
    if not s:
        return {"status": "unknown"}
    return s
