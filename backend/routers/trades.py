from fastapi import APIRouter, Depends, Query, UploadFile, File
from typing import Optional
from pydantic import BaseModel

from ..auth.dependencies import get_current_user

router = APIRouter(prefix="/api/trades", tags=["交易记录"])


class TradeCreate(BaseModel):
    ts_code: str
    trade_date: str
    action: str
    price: float
    volume: int
    profit_loss: float = 0


@router.get("")
async def list_trades(
    limit: int = Query(50, le=200),
    _=Depends(get_current_user)
):
    from ..app import get_sqlite_client
    db = get_sqlite_client()
    with db.get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM {db.LEGACY_TRADES_TABLE} ORDER BY trade_date DESC, id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("")
async def create_trade(data: TradeCreate, _=Depends(get_current_user)):
    from ..app import get_sqlite_client
    db = get_sqlite_client()
    with db.get_connection() as conn:
        cursor = conn.execute(f"""
            INSERT INTO {db.LEGACY_TRADES_TABLE} (ts_code, trade_date, action, price, volume, profit_loss)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (data.ts_code, data.trade_date, data.action, data.price, data.volume, data.profit_loss))
        conn.commit()
        return {"id": cursor.lastrowid, "detail": "已录入"}


@router.post("/upload-image")
async def upload_trade_image(file: UploadFile = File(...), _=Depends(get_current_user)):
    """上传交割单图片进行OCR识别"""
    contents = await file.read()
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.write(contents)
    tmp.close()

    try:
        from backend.services.settings_service import SettingsService
        from backend.app import get_sqlite_client
        from src.llm.factory import LLMFactory

        svc = SettingsService(get_sqlite_client())
        provider = svc.get_raw_value("llm", "provider") or "openai"
        api_key = svc.get_raw_value("llm", "api_key")
        api_base = svc.get_raw_value("llm", "api_base")
        model = svc.get_raw_value("llm", "model") or "gpt-4"

        llm = LLMFactory.create(provider, api_key=api_key, api_base=api_base, model=model)
        from src.agents.act.trade_recorder import TradeRecorder
        recorder = TradeRecorder(llm, get_sqlite_client())
        result = recorder.parse_trade_image(tmp.name)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        os.unlink(tmp.name)
