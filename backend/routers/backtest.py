from fastapi import APIRouter, Depends, Query
from loguru import logger

from ..auth.dependencies import get_current_user
from ..services.settings_service import SettingsService
from ..services.usage_log_service import UsageLogService
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


def _get_usage_log_service() -> UsageLogService:
    from ..app import get_sqlite_client

    return UsageLogService(get_sqlite_client())


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
    current_user=Depends(get_current_user)
):
    from ..app import get_sqlite_client

    db = get_sqlite_client()
    settings = SettingsService(db)
    if mode == "review":
        token = settings.get_raw_value("tushare", "token")
        api_url = settings.get_raw_value("tushare", "api_url") or ""
        if not token:
            error_result = {"mode": "review", "error": "请先配置Tushare Token"}
            _record_backtest_log_safely(
                current_user=current_user,
                mode=mode,
                model_type=model_type,
                start_date=start_date,
                end_date=end_date,
                hold_days=hold_days,
                top_n=top_n,
                train_window_days=train_window_days,
                max_features=max_features,
                symbols=[],
                result=error_result,
            )
            return error_result

        tushare_api = TushareAPI(token, api_url=api_url)
        engine = BacktestEngine(db, tushare_api)
        result = engine.run_backtest(start_date, end_date, hold_days)
        payload = {"mode": "review", **result}
        _record_backtest_log_safely(
            current_user=current_user,
            mode=mode,
            model_type=model_type,
            start_date=start_date,
            end_date=end_date,
            hold_days=hold_days,
            top_n=top_n,
            train_window_days=train_window_days,
            max_features=max_features,
            symbols=[],
            result=payload,
        )
        return payload

    resolved_symbols = _parse_symbols(symbols)
    if not resolved_symbols:
        market_symbols = settings.get_raw_value("market_data", "symbols") or ""
        resolved_symbols = _parse_symbols(market_symbols)

    try:
        engine = PortfolioBacktestEngine(db)
        result = engine.run_factor_backtest(
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
        _record_backtest_log_safely(
            current_user=current_user,
            mode=mode,
            model_type=model_type,
            start_date=start_date,
            end_date=end_date,
            hold_days=hold_days,
            top_n=top_n,
            train_window_days=train_window_days,
            max_features=max_features,
            symbols=resolved_symbols,
            result=result,
        )
        return result
    except ValueError as exc:
        error_result = {"mode": "portfolio", "model_type": model_type, "error": str(exc)}
        _record_backtest_log_safely(
            current_user=current_user,
            mode=mode,
            model_type=model_type,
            start_date=start_date,
            end_date=end_date,
            hold_days=hold_days,
            top_n=top_n,
            train_window_days=train_window_days,
            max_features=max_features,
            symbols=resolved_symbols,
            result=error_result,
        )
        return error_result


def _record_backtest_log_safely(
    *,
    current_user: dict,
    mode: str,
    model_type: str,
    start_date: str,
    end_date: str,
    hold_days: int,
    top_n: int,
    train_window_days: int,
    max_features: int,
    symbols: list[str],
    result: dict,
) -> None:
    try:
        _get_usage_log_service().record_backtest_run(
            current_user,
            mode=mode,
            model_type=model_type,
            start_date=start_date,
            end_date=end_date,
            hold_days=hold_days,
            top_n=top_n,
            train_window_days=train_window_days,
            max_features=max_features,
            symbols=symbols,
            result=result,
        )
    except Exception as exc:  # pragma: no cover - 日志失败不应中断主流程
        logger.warning("记录回测日志失败: {}", exc)
