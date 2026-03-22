from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from ..data.db.sqlite_client import SQLiteClient
from .portfolio_engine import PortfolioBacktestEngine


class WalkForwardRunner:
    """滚动训练 / 滚动回测骨架，后续可在此基础上继续增强。"""

    def __init__(self, sqlite_client: SQLiteClient):
        self.engine = PortfolioBacktestEngine(sqlite_client)

    def build_windows(
        self,
        start_date: str,
        end_date: str,
        train_window_days: int = 120,
        test_window_days: int = 20,
    ) -> List[Dict]:
        start_dt = pd.Timestamp(start_date)
        end_dt = pd.Timestamp(end_date)
        cursor = start_dt
        windows: List[Dict] = []
        while cursor <= end_dt:
            test_end = min(cursor + pd.Timedelta(days=test_window_days - 1), end_dt)
            windows.append(
                {
                    "train_start_date": (cursor - pd.Timedelta(days=train_window_days)).strftime("%Y-%m-%d"),
                    "train_end_date": (cursor - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                    "test_start_date": cursor.strftime("%Y-%m-%d"),
                    "test_end_date": test_end.strftime("%Y-%m-%d"),
                }
            )
            cursor = test_end + pd.Timedelta(days=1)
        return windows

    def run(
        self,
        start_date: str,
        end_date: str,
        symbols: Optional[List[str]] = None,
        train_window_days: int = 120,
        test_window_days: int = 20,
        hold_days: int = 5,
        top_n: int = 5,
    ) -> Dict:
        windows = self.build_windows(
            start_date=start_date,
            end_date=end_date,
            train_window_days=train_window_days,
            test_window_days=test_window_days,
        )
        results = []
        for window in windows:
            result = self.engine.run_factor_backtest(
                start_date=window["test_start_date"],
                end_date=window["test_end_date"],
                symbols=symbols,
                hold_days=hold_days,
                top_n=top_n,
                train_window_days=train_window_days,
            )
            results.append(
                {
                    "window": window,
                    "summary": result["summary"],
                    "selected_features": result["selected_features"],
                }
            )
        return {"windows": windows, "results": results}
