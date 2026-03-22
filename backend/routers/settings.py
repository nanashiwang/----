import json
from urllib.parse import urlparse

import requests
from fastapi import APIRouter, Depends

from ..auth.dependencies import get_current_user, require_admin
from ..models.settings import SettingsOut, SettingsUpdate, TestLLMRequest, TestTushareRequest
from ..services.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["系统配置"])

_RESPONSES_MODEL_PREFIXES = ("gpt-5", "o1", "o3", "o4")


def _normalize_api_base(api_base: str) -> str:
    normalized = api_base.rstrip("/")
    parsed = urlparse(normalized)
    if parsed.path in ("", "/"):
        return f"{normalized}/v1"
    return normalized


def _should_use_responses_test(provider: str, model: str) -> bool:
    provider_name = (provider or "").lower()
    model_name = (model or "").lower()
    return provider_name in {"openai", "custom"} and (
        "codex" in model_name or model_name.startswith(_RESPONSES_MODEL_PREFIXES)
    )


def _test_responses_stream(api_base: str, api_key: str, model: str) -> dict:
    url = f"{_normalize_api_base(api_base)}/responses"
    payload = {
        "model": model,
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "请回复ok",
                    }
                ],
            }
        ],
        "stream": True,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream",
        "User-Agent": "quant-trading-llm-test",
    }

    with requests.post(url, headers=headers, json=payload, stream=True, timeout=(10, 45)) as response:
        response.raise_for_status()

        first_event = None
        first_data = None
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("event:"):
                first_event = line.split(":", 1)[1].strip()
                break
            if line.startswith("data:") and first_data is None:
                raw_data = line.split(":", 1)[1].strip()
                try:
                    first_data = json.loads(raw_data)
                except json.JSONDecodeError:
                    first_data = raw_data

        if first_event:
            return {"success": True, "message": f"连接成功: 已收到流式事件 {first_event}"}
        if first_data:
            return {"success": True, "message": "连接成功: 已收到响应数据"}
        return {"success": True, "message": "连接成功: 已建立流式连接"}


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
        if _should_use_responses_test(data.provider, data.model):
            return _test_responses_stream(data.api_base, data.api_key, data.model)

        from src.llm.factory import LLMFactory

        llm = LLMFactory.create(
            data.provider,
            api_key=data.api_key,
            api_base=data.api_base,
            model=data.model,
        )
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
        return {"success": True, "message": f"连接成功，共 {len(df)} 只股票"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}
