from typing import Dict, List, Any
from datetime import datetime, timedelta
import pandas as pd
from ..data.db.sqlite_client import SQLiteClient
from ..data.sources.tushare_api import TushareAPI


class BacktestEngine:
    """回测引擎"""

    def __init__(self, sqlite_client: SQLiteClient, tushare_api: TushareAPI):
        self.db = sqlite_client
        self.ts = tushare_api

    def load_recommendations(self, start_date: str, end_date: str) -> pd.DataFrame:
        """加载推荐记录"""
        with self.db.get_connection() as conn:
            return pd.read_sql(
                f"SELECT * FROM {self.db.LEGACY_RECOMMENDATIONS_TABLE} WHERE date BETWEEN ? AND ?",
                conn, params=(start_date, end_date)
            )

    def calculate_returns(self, ts_code: str, buy_date: str, hold_days: int = 5) -> Dict:
        """计算收益率"""
        start = datetime.strptime(buy_date, "%Y-%m-%d")
        end = start + timedelta(days=hold_days + 5)

        df = self.ts.get_daily_data(
            ts_code,
            start.strftime("%Y%m%d"),
            end.strftime("%Y%m%d")
        )

        if df.empty or len(df) < 2:
            return {"error": "数据不足"}

        df = df.sort_values('trade_date')
        buy_price = df.iloc[0]['close']

        if len(df) <= hold_days:
            sell_price = df.iloc[-1]['close']
        else:
            sell_price = df.iloc[hold_days]['close']

        return_rate = (sell_price - buy_price) / buy_price
        return {
            "buy_price": float(buy_price),
            "sell_price": float(sell_price),
            "return_rate": float(return_rate),
            "hold_days": hold_days
        }

    def run_backtest(self, start_date: str, end_date: str, hold_days: int = 5) -> Dict[str, Any]:
        """运行回测"""
        recs = self.load_recommendations(start_date, end_date)

        if recs.empty:
            return {"error": "无推荐数据"}

        results = []
        for _, rec in recs.iterrows():
            ret = self.calculate_returns(rec['ts_code'], rec['date'], hold_days)
            if "error" not in ret:
                results.append({
                    "date": rec['date'],
                    "ts_code": rec['ts_code'],
                    "weight": rec['weight'],
                    "return_rate": ret['return_rate']
                })

        if not results:
            return {"error": "无有效回测结果"}

        df_results = pd.DataFrame(results)

        return {
            "total_trades": len(results),
            "win_rate": (df_results['return_rate'] > 0).mean(),
            "avg_return": df_results['return_rate'].mean(),
            "max_return": df_results['return_rate'].max(),
            "min_return": df_results['return_rate'].min(),
            "details": results
        }
