from fastapi import APIRouter, Depends, HTTPException
from typing import List
import json

from ..models.settings import NewsSourceCreate, NewsSourceOut
from ..auth.dependencies import get_current_user, require_admin
from ..services.source_service import SourceService

router = APIRouter(prefix="/api/sources", tags=["资讯源管理"])


def _get_service():
    from ..app import get_sqlite_client
    return SourceService(get_sqlite_client())


@router.get("", response_model=List[NewsSourceOut])
async def list_sources(_=Depends(get_current_user)):
    svc = _get_service()
    rows = svc.list_all()
    return [NewsSourceOut(**r) for r in rows]


@router.post("", response_model=NewsSourceOut)
async def create_source(data: NewsSourceCreate, _=Depends(require_admin)):
    svc = _get_service()
    sid = svc.create(data.model_dump())
    row = svc.get_by_id(sid)
    return NewsSourceOut(**row)


@router.put("/{source_id}", response_model=NewsSourceOut)
async def update_source(source_id: int, data: NewsSourceCreate, _=Depends(require_admin)):
    svc = _get_service()
    if not svc.get_by_id(source_id):
        raise HTTPException(status_code=404, detail="资讯源不存在")
    svc.update(source_id, data.model_dump())
    row = svc.get_by_id(source_id)
    return NewsSourceOut(**row)


@router.delete("/{source_id}")
async def delete_source(source_id: int, _=Depends(require_admin)):
    svc = _get_service()
    if not svc.get_by_id(source_id):
        raise HTTPException(status_code=404, detail="资讯源不存在")
    svc.delete(source_id)
    return {"detail": "已删除"}


@router.post("/{source_id}/fetch")
async def fetch_source(source_id: int, _=Depends(require_admin)):
    svc = _get_service()
    source = svc.get_by_id(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="资讯源不存在")

    config = json.loads(source["config"])
    source_type = source["type"]

    try:
        if source_type == "rss":
            from src.data.sources.rss_source import fetch_rss
            articles = fetch_rss(config["url"])
        elif source_type == "crawler":
            from src.data.sources.crawler_source import fetch_crawler
            articles = fetch_crawler(config)
        elif source_type == "tushare":
            from src.data.sources.tushare_api import TushareAPI
            from backend.services.settings_service import SettingsService
            from backend.app import get_sqlite_client
            token = SettingsService(get_sqlite_client()).get_raw_value("tushare", "token")
            api = TushareAPI(token)
            from datetime import datetime
            today = datetime.now().strftime("%Y%m%d")
            df = api.get_news(today, today)
            articles = df.to_dict("records") if not df.empty else []
        else:
            articles = []

        svc.update_last_fetched(source_id)
        return {"success": True, "count": len(articles), "articles": articles[:5]}
    except Exception as e:
        return {"success": False, "message": str(e)}
