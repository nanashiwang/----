from typing import Dict, List

import pandas as pd


def build_equity_curve(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series | None = None,
) -> pd.DataFrame:
    curve = pd.DataFrame(index=strategy_returns.index.sort_values())
    curve["daily_return"] = strategy_returns.reindex(curve.index).fillna(0.0)
    curve["nav"] = (1.0 + curve["daily_return"]).cumprod()
    curve["drawdown"] = curve["nav"] / curve["nav"].cummax() - 1.0

    if benchmark_returns is not None:
        curve["benchmark_return"] = benchmark_returns.reindex(curve.index).fillna(0.0)
        curve["benchmark_nav"] = (1.0 + curve["benchmark_return"]).cumprod()
    else:
        curve["benchmark_return"] = 0.0
        curve["benchmark_nav"] = 1.0

    return curve.reset_index().rename(columns={"index": "trade_date"})


def summarize_backtest(
    equity_curve: pd.DataFrame,
    trades: List[Dict],
    turnover_series: pd.Series,
) -> Dict:
    if equity_curve.empty:
        return {
            "trade_count": 0,
            "signal_days": 0,
            "win_rate": 0.0,
            "avg_trade_return": 0.0,
            "cumulative_return": 0.0,
            "benchmark_cumulative_return": 0.0,
            "excess_return": 0.0,
            "annualized_return": 0.0,
            "benchmark_annualized_return": 0.0,
            "annualized_excess_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe": 0.0,
            "turnover_rate": 0.0,
            "annualized_turnover": 0.0,
        }

    strategy_nav = float(equity_curve.iloc[-1]["nav"])
    benchmark_nav = float(equity_curve.iloc[-1]["benchmark_nav"])
    periods = len(equity_curve)
    annual_factor = 252 / periods if periods else 0.0

    daily_return = equity_curve["daily_return"].fillna(0.0)
    daily_std = float(daily_return.std(ddof=0))
    sharpe = 0.0
    if daily_std > 1e-12:
        sharpe = float(daily_return.mean() / daily_std * (252**0.5))

    cumulative_return = strategy_nav - 1.0
    benchmark_cumulative_return = benchmark_nav - 1.0
    annualized_return = strategy_nav**annual_factor - 1.0 if strategy_nav > 0 and periods else 0.0
    benchmark_annualized_return = (
        benchmark_nav**annual_factor - 1.0 if benchmark_nav > 0 and periods else 0.0
    )

    avg_trade_return = 0.0
    win_rate = 0.0
    if trades:
        trade_returns = pd.Series([item["net_return"] for item in trades], dtype=float)
        avg_trade_return = float(trade_returns.mean())
        win_rate = float((trade_returns > 0).mean())

    turnover_rate = float(turnover_series.mean()) if len(turnover_series) else 0.0
    return {
        "trade_count": len(trades),
        "signal_days": len({item["signal_date"] for item in trades}),
        "win_rate": win_rate,
        "avg_trade_return": avg_trade_return,
        "cumulative_return": cumulative_return,
        "benchmark_cumulative_return": benchmark_cumulative_return,
        "excess_return": cumulative_return - benchmark_cumulative_return,
        "annualized_return": annualized_return,
        "benchmark_annualized_return": benchmark_annualized_return,
        "annualized_excess_return": annualized_return - benchmark_annualized_return,
        "max_drawdown": float(equity_curve["drawdown"].min()),
        "sharpe": sharpe,
        "turnover_rate": turnover_rate,
        "annualized_turnover": turnover_rate * 252,
    }
