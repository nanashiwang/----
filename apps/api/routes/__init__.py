from fastapi import APIRouter

from apps.api.routes.knowledge import router as knowledge_router
from apps.api.routes.ml import router as ml_router
from apps.api.routes.trades import router as trade_router
from apps.api.routes.workflow import router as workflow_router

api_router = APIRouter()
api_router.include_router(workflow_router)
api_router.include_router(knowledge_router)
api_router.include_router(trade_router)
api_router.include_router(ml_router)
