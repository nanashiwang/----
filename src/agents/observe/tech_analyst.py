from typing import Dict, Any, List
import pandas as pd
from ...data.sources.tushare_api import TushareAPI
from ...data.db.sqlite_client import SQLiteClient


class TechAnalyst:
    """技术指标专员 - 分析股票技术指标"""

    def __init__(self, tushare_api: TushareAPI, sqlite_client: SQLiteClient):
        self.ts = tushare_api
        self.db = sqlite_client

    def calculate_ma(self, df: pd.DataFrame, periods: List[int] = [5, 10, 20]) -> pd.DataFrame:
        """计算移动平均线"""
        for period in periods:
            df[f'ma{period}'] = df['close'].rolling(window=period).mean()
        return df

    def calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算MACD"""
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['hist'] = df['macd'] - df['signal']
        return df

    def analyze_stock(self, ts_code: str, days: int = 60) -> Dict[str, Any]:
        """分析单只股票"""
        end_date = pd.Timestamp.now().strftime("%Y%m%d")
        start_date = (pd.Timestamp.now() - pd.Timedelta(days=days)).strftime("%Y%m%d")

        df = self.ts.get_daily_data(ts_code, start_date, end_date)
        if df.empty:
            return {"ts_code": ts_code, "error": "无数据"}

        df = df.sort_values('trade_date')
        df = self.calculate_ma(df)
        df = self.calculate_macd(df)

        latest = df.iloc[-1]
        return {
            "ts_code": ts_code,
            "close": float(latest['close']),
            "ma5": float(latest['ma5']) if pd.notna(latest['ma5']) else None,
            "ma10": float(latest['ma10']) if pd.notna(latest['ma10']) else None,
            "ma20": float(latest['ma20']) if pd.notna(latest['ma20']) else None,
            "macd": float(latest['macd']) if pd.notna(latest['macd']) else None,
            "signal": float(latest['signal']) if pd.notna(latest['signal']) else None,
            "volume": float(latest['vol'])
        }

    def save_stock_data(self, ts_code: str, df: pd.DataFrame):
        """保存股票数据"""
        with self.db.get_connection() as conn:
            for _, row in df.iterrows():
                conn.execute("""
                    INSERT OR REPLACE INTO stock_data
                    (ts_code, trade_date, open, close, high, low, volume, amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (ts_code, row['trade_date'], row['open'], row['close'],
                      row['high'], row['low'], row['vol'], row['amount']))
            conn.commit()

    def run(self, stock_codes: List[str]) -> Dict[str, Any]:
        """执行技术分析"""
        results = {}
        for code in stock_codes:
            results[code] = self.analyze_stock(code)
        return {"tech_data": results}
