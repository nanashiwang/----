from datetime import datetime, timedelta
from typing import Dict, Optional

import pandas as pd
import tushare as ts


def _normalize_http_url(api_url: str) -> str:
    normalized = (api_url or "").strip()
    if not normalized:
        return ""
    return normalized if normalized.endswith("/") else f"{normalized}/"


class TushareAPI:
    def __init__(self, token: str, api_url: str = ""):
        self.token = token
        self.api_url = _normalize_http_url(api_url)
        self.pro = ts.pro_api(token)
        if self.api_url:
            self.pro._DataApi__http_url = self.api_url

    def get_stock_basic(self, exchange: Optional[str] = None) -> pd.DataFrame:
        return self.pro.stock_basic(
            exchange=exchange,
            list_status="L",
            fields="ts_code,symbol,name,area,industry,market",
        )

    def get_index_basic(self, limit: int = 5) -> pd.DataFrame:
        return self.pro.index_basic(
            limit=limit,
            fields="ts_code,name,market,publisher,category,base_date",
        )

    def get_daily_data(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

    def get_daily_basic(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self.pro.daily_basic(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields="ts_code,trade_date,turnover_rate,volume_ratio,pe,pb",
        )

    def get_index_daily(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self.pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

    def get_news(self, start_date: str, end_date: str, src: str = "sina") -> pd.DataFrame:
        return self.pro.news(start_date=start_date, end_date=end_date, src=src)

    def get_major_news(self, start_date: str, end_date: str, src: str = "") -> pd.DataFrame:
        return self.pro.major_news(start_date=start_date, end_date=end_date, src=src)

    def get_announcements(self, ann_date: Optional[str] = None) -> pd.DataFrame:
        if ann_date:
            return self.pro.anns_d(ann_date=ann_date)
        return self.pro.anns_d(ann_date=datetime.now().strftime("%Y%m%d"))

    def get_irm_qa_sh(self, trade_date: Optional[str] = None) -> pd.DataFrame:
        if trade_date:
            return self.pro.irm_qa_sh(trade_date=trade_date)
        return self.pro.irm_qa_sh(trade_date=datetime.now().strftime("%Y%m%d"))

    def get_irm_qa_sz(self, trade_date: Optional[str] = None) -> pd.DataFrame:
        if trade_date:
            return self.pro.irm_qa_sz(trade_date=trade_date)
        return self.pro.irm_qa_sz(trade_date=datetime.now().strftime("%Y%m%d"))

    def get_report_rc(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        end_val = end_date or datetime.now().strftime("%Y%m%d")
        start_val = start_date or (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
        return self.pro.report_rc(start_date=start_val, end_date=end_val)

    def fetch_dataset(self, dataset: str, params: Optional[Dict] = None) -> pd.DataFrame:
        params = params or {}
        if dataset == "news":
            return self.get_news(
                params.get("start_date", datetime.now().strftime("%Y%m%d")),
                params.get("end_date", datetime.now().strftime("%Y%m%d")),
                src=params.get("src", "sina"),
            )
        if dataset == "major_news":
            return self.get_major_news(
                params.get("start_date", datetime.now().strftime("%Y%m%d")),
                params.get("end_date", datetime.now().strftime("%Y%m%d")),
                src=params.get("src", ""),
            )
        if dataset == "anns_d":
            return self.get_announcements(params.get("ann_date"))
        if dataset == "irm_qa_sh":
            return self.get_irm_qa_sh(params.get("trade_date"))
        if dataset == "irm_qa_sz":
            return self.get_irm_qa_sz(params.get("trade_date"))
        if dataset == "report_rc":
            return self.get_report_rc(params.get("start_date"), params.get("end_date"))
        raise ValueError(f"不支持的 Tushare 数据集: {dataset}")

    def get_top_list(self, trade_date: str) -> pd.DataFrame:
        return self.pro.top_list(trade_date=trade_date)

    def get_moneyflow(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self.pro.moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
