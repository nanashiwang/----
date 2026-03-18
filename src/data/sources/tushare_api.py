import tushare as ts
import pandas as pd
from typing import Optional, List
from datetime import datetime, timedelta


class TushareAPI:
    def __init__(self, token: str):
        ts.set_token(token)
        self.pro = ts.pro_api()

    def get_stock_basic(self, exchange: Optional[str] = None) -> pd.DataFrame:
        """获取股票列表"""
        return self.pro.stock_basic(exchange=exchange, list_status='L',
                                    fields='ts_code,symbol,name,area,industry,market')

    def get_daily_data(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取日线数据"""
        return self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

    def get_daily_basic(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取每日指标"""
        return self.pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date,
                                    fields='ts_code,trade_date,turnover_rate,volume_ratio,pe,pb')

    def get_news(self, start_date: str, end_date: str, src: str = 'sina') -> pd.DataFrame:
        """获取新闻数据"""
        return self.pro.news(start_date=start_date, end_date=end_date, src=src)

    def get_top_list(self, trade_date: str) -> pd.DataFrame:
        """获取龙虎榜数据"""
        return self.pro.top_list(trade_date=trade_date)

    def get_moneyflow(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取资金流向"""
        return self.pro.moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
