from fastapi import APIRouter, Depends, Query

from ..auth.dependencies import get_current_user

router = APIRouter(prefix="/api/backtest", tags=["回测系统"])


@router.post("")
async def run_backtest(
    start_date: str,
    end_date: str,
    hold_days: int = Query(5, ge=1, le=30),
    _=Depends(get_current_user)
):
    from ..app import get_sqlite_client
    from backend.services.settings_service import SettingsService
    from src.data.sources.tushare_api import TushareAPI
    from src.backtest.engine import BacktestEngine

    db = get_sqlite_client()
    token = SettingsService(db).get_raw_value("tushare", "token")
    if not token:
        return {"error": "请先配置Tushare Token"}

    tushare_api = TushareAPI(token)
    engine = BacktestEngine(db, tushare_api)
    result = engine.run_backtest(start_date, end_date, hold_days)
    return result
