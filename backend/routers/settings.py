from fastapi import APIRouter, Depends, HTTPException
from typing import List

from ..models.settings import SettingsUpdate, SettingsOut, TestLLMRequest, TestTushareRequest
from ..auth.dependencies import get_current_user, require_admin
from ..services.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["系统配置"])


def _get_service():
    from ..app import get_sqlite_client
    return SettingsService(get_sqlite_client())


@router.get("/{category}", response_model=SettingsOut)
async def get_settings(category: str, _=Depends(get_current_user)):
    svc = _get_service()
    items = svc.get_settings(category)
    return SettingsOut(category=category, settings=items)


@router.put("/{category}")
async def update_settings(category: str, data: SettingsUpdate, user=Depends(require_admin)):
    svc = _get_service()
    svc.update_settings(category, [item.model_dump() for item in data.settings], user.get("uid"))
    return {"detail": "配置已更新"}


@router.post("/test-llm")
async def test_llm(data: TestLLMRequest, _=Depends(require_admin)):
    try:
        from src.llm.factory import LLMFactory
        llm = LLMFactory.create(data.provider, api_key=data.api_key, api_base=data.api_base, model=data.model)
        result = llm.chat([{"role": "user", "content": "请回复ok"}])
        return {"success": True, "message": f"连接成功: {result[:50]}"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}


@router.post("/test-tushare")
async def test_tushare(data: TestTushareRequest, _=Depends(require_admin)):
    try:
        from src.data.sources.tushare_api import TushareAPI
        api = TushareAPI(data.token)
        df = api.get_stock_basic()
        return {"success": True, "message": f"连接成功，共{len(df)}只股票"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}
