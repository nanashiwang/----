from fastapi import APIRouter, Depends, Query

from ..auth.dependencies import get_current_user
from ..services.settings_service import SettingsService
from src.backtest.engine import BacktestEngine
from src.backtest.portfolio_engine import PortfolioBacktestEngine
from src.data.sources.tushare_api import TushareAPI

router = APIRouter(prefix="/api/backtest", tags=["回测系统"])


def _parse_symbols(symbols: str) -> list[str]:
    return [
        item.strip().upper()
        for item in str(symbols or "").replace("\n", ",").replace("，", ",").split(",")
        if item.strip()
    ]


@router.post("")
async def run_backtest(
    start_date: str,
    end_date: str,
    mode: str = Query("review", pattern="^(review|portfolio)$"),
    model_type: str = Query("linear_factor", pattern="^(linear_factor|sklearn_ridge|compare)$"),
    hold_days: int = Query(5, ge=1, le=30),
    top_n: int = Query(5, ge=1, le=50),
    fee_rate: float = Query(0.0005, ge=0.0, le=0.02),
    slippage_rate: float = Query(0.0005, ge=0.0, le=0.02),
    train_window_days: int = Query(120, ge=30, le=720),
    max_features: int = Query(6, ge=1, le=20),
    symbols: str = "",
    _=Depends(get_current_user)
):
    from ..app import get_sqlite_client

    db = get_sqlite_client()
    settings = SettingsService(db)
    if mode == "review":
        token = settings.get_raw_value("tushare", "token")
        api_url = settings.get_raw_value("tushare", "api_url") or ""
        if not token:
            return {"mode": "review", "error": "请先配置Tushare Token"}

        tushare_api = TushareAPI(token, api_url=api_url)
        engine = BacktestEngine(db, tushare_api)
        result = engine.run_backtest(start_date, end_date, hold_days)
        return {"mode": "review", **result}

    resolved_symbols = _parse_symbols(symbols)
    if not resolved_symbols:
        market_symbols = settings.get_raw_value("market_data", "symbols") or ""
        resolved_symbols = _parse_symbols(market_symbols)

    try:
        engine = PortfolioBacktestEngine(db)
        return engine.run_factor_backtest(
            start_date=start_date,
            end_date=end_date,
            symbols=resolved_symbols,
            hold_days=hold_days,
            top_n=top_n,
            fee_rate=fee_rate,
            slippage_rate=slippage_rate,
            train_window_days=train_window_days,
            max_features=max_features,
            model_type=model_type,
        )
    except ValueError as exc:
        return {"mode": "portfolio", "model_type": model_type, "error": str(exc)}
