import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.market_data_service import MarketDataService
from backend.services.settings_service import SettingsService
from src.data.db.sqlite_client import SQLiteClient


class _FakeTushareAPI:
    def __init__(self, token, api_url=""):
        self.token = token
        self.api_url = api_url

    def get_daily_data(self, ts_code, start_date, end_date):
        return pd.DataFrame(
            [
                {
                    "ts_code": ts_code,
                    "trade_date": "20260320",
                    "open": 10.0,
                    "close": 10.5,
                    "high": 10.8,
                    "low": 9.9,
                    "vol": 123456,
                    "amount": 456789,
                }
            ]
        )

    def get_daily_basic(self, ts_code, start_date, end_date):
        return pd.DataFrame(
            [
                {
                    "ts_code": ts_code,
                    "trade_date": "20260320",
                    "turnover_rate": 2.5,
                    "volume_ratio": 1.2,
                    "pe": 15.6,
                    "pb": 3.2,
                }
            ]
        )

    def get_moneyflow(self, ts_code, start_date, end_date):
        return pd.DataFrame(
            [
                {
                    "ts_code": ts_code,
                    "trade_date": "20260320",
                    "buy_lg_amount": 1000,
                    "sell_lg_amount": 900,
                    "net_mf_amount": 500,
                }
            ]
        )

    def get_top_list(self, trade_date):
        return pd.DataFrame([])

    def get_index_daily(self, ts_code, start_date, end_date):
        return pd.DataFrame(
            [
                {
                    "ts_code": ts_code,
                    "trade_date": "20260320",
                    "open": 3980.0,
                    "close": 4012.0,
                    "high": 4021.0,
                    "low": 3972.0,
                    "pre_close": 3976.0,
                    "change": 36.0,
                    "pct_chg": 0.91,
                    "vol": 321000000,
                    "amount": 456000000000,
                }
            ]
        )

    def get_stock_basic(self, exchange=None):
        return pd.DataFrame(
            [
                {
                    "ts_code": "688981.SH",
                    "symbol": "688981",
                    "name": "中芯国际",
                    "area": "上海",
                    "industry": "半导体",
                    "market": "科创板",
                },
                {
                    "ts_code": "300750.SZ",
                    "symbol": "300750",
                    "name": "宁德时代",
                    "area": "深圳",
                    "industry": "电池",
                    "market": "创业板",
                },
                {
                    "ts_code": "600519.SH",
                    "symbol": "600519",
                    "name": "贵州茅台",
                    "area": "贵州",
                    "industry": "白酒",
                    "market": "主板",
                },
            ]
        )


class _PartiallyFailingTushareAPI(_FakeTushareAPI):
    def get_moneyflow(self, ts_code, start_date, end_date):
        if ts_code == "600519.SH":
            raise RuntimeError("moneyflow 接口异常")
        return super().get_moneyflow(ts_code, start_date, end_date)


class TestMarketDataService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = SQLiteClient(str(Path(self.temp_dir.name) / "market.db"))
        self.settings = SettingsService(self.db)
        self.settings.update_settings(
            "tushare",
            [
                {"key": "token", "value": "test-token", "is_secret": True},
                {"key": "api_url", "value": "http://127.0.0.1:8010/", "is_secret": False},
            ],
        )
        self.settings.update_settings(
            "market_data",
            [
                {"key": "symbols", "value": "000001.SZ,600519.SH", "is_secret": False},
                {"key": "data_types", "value": "daily,daily_basic,moneyflow,index_daily", "is_secret": False},
                {"key": "benchmark_index_codes", "value": "000300.SH,000001.SH", "is_secret": False},
                {"key": "primary_benchmark", "value": "000300.SH", "is_secret": False},
                {"key": "fetch_interval", "value": "3600", "is_secret": False},
                {"key": "history_days", "value": "15", "is_secret": False},
                {"key": "start_date", "value": "", "is_secret": False},
                {"key": "end_date", "value": "", "is_secret": False},
                {"key": "auto_sync", "value": "true", "is_secret": False},
            ],
        )
        self.service = MarketDataService(self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_get_sync_settings_parses_configured_values(self):
        settings = self.service.get_sync_settings()

        self.assertEqual(settings["symbols"], ["000001.SZ", "600519.SH"])
        self.assertEqual(settings["data_types"], ["daily", "daily_basic", "moneyflow", "index_daily"])
        self.assertEqual(settings["benchmark_index_codes"], ["000300.SH", "000001.SH"])
        self.assertEqual(settings["primary_benchmark"], "000300.SH")
        self.assertEqual(settings["fetch_interval"], 3600)
        self.assertEqual(settings["history_days"], 15)
        self.assertEqual(settings["start_date"], "")
        self.assertEqual(settings["end_date"], "")
        self.assertTrue(settings["auto_sync"])

    def test_get_sync_settings_normalizes_plain_symbols(self):
        self.settings.update_settings(
            "market_data",
            [
                {"key": "symbols", "value": "688981,000001,430047", "is_secret": False},
            ],
        )

        settings = self.service.get_sync_settings()

        self.assertEqual(settings["symbols"], ["688981.SH", "000001.SZ", "430047.BJ"])

    def test_sync_configured_data_writes_daily_and_snapshot_rows(self):
        progress_events = []
        with patch("backend.services.market_data_service.TushareAPI", _FakeTushareAPI):
            result = self.service.sync_configured_data(progress_callback=progress_events.append)

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["symbol_count"], 2)
        self.assertEqual(result["daily_rows"], 2)
        self.assertEqual(result["snapshot_rows"], 4)
        self.assertEqual(result["index_rows"], 2)
        self.assertEqual(result["benchmark_index_codes"], ["000300.SH", "000001.SH"])
        self.assertEqual(result["primary_benchmark"], "000300.SH")
        self.assertGreaterEqual(len(progress_events), 1)
        self.assertEqual(progress_events[-1]["current"], progress_events[-1]["total"])

        overview = self.service.get_overview(ts_code="000001.SZ")
        self.assertEqual(overview["ts_code"], "000001.SZ")
        self.assertEqual(len(overview["records"]), 1)
        record = overview["records"][0]
        self.assertEqual(record["trade_date"], "2026-03-20")
        self.assertEqual(record["close"], 10.5)
        self.assertEqual(record["pe"], 15.6)
        self.assertEqual(record["net_mf_amount"], 500)
        self.assertEqual(overview["primary_benchmark"], "000300.SH")
        self.assertEqual(overview["benchmark_index_codes"], ["000300.SH", "000001.SH"])
        self.assertEqual(overview["benchmark_summary"]["index_code"], "000300.SH")
        self.assertEqual(overview["benchmark_summary"]["close"], 4012.0)
        self.assertEqual(len(overview["benchmark_series"]), 1)
        self.assertEqual(overview["runtime"]["last_sync_status"], "success")
        self.assertEqual(overview["sync_window"]["history_days"], 15)

    def test_sync_configured_data_supports_benchmark_only(self):
        self.settings.update_settings(
            "market_data",
            [
                {"key": "symbols", "value": "", "is_secret": False},
                {"key": "data_types", "value": "index_daily", "is_secret": False},
                {"key": "benchmark_index_codes", "value": "000300.SH", "is_secret": False},
                {"key": "primary_benchmark", "value": "000300.SH", "is_secret": False},
            ],
        )

        with patch("backend.services.market_data_service.TushareAPI", _FakeTushareAPI):
            result = self.service.sync_configured_data()

        self.assertTrue(result["success"])
        self.assertEqual(result["symbol_count"], 0)
        self.assertEqual(result["daily_rows"], 0)
        self.assertEqual(result["snapshot_rows"], 0)
        self.assertEqual(result["index_rows"], 1)

        overview = self.service.get_overview()
        self.assertEqual(overview["ts_code"], "")
        self.assertFalse(overview["records"])
        self.assertEqual(overview["benchmark_summary"]["index_code"], "000300.SH")
        self.assertEqual(len(overview["benchmark_series"]), 1)

    def test_sync_configured_data_respects_explicit_date_range(self):
        self.settings.update_settings(
            "market_data",
            [
                {"key": "start_date", "value": "2026-03-01", "is_secret": False},
                {"key": "end_date", "value": "2026-03-20", "is_secret": False},
            ],
        )

        with patch("backend.services.market_data_service.TushareAPI", _FakeTushareAPI):
            result = self.service.sync_configured_data(mode="backfill")

        self.assertEqual(result["range_start"], "2026-03-01")
        self.assertEqual(result["range_end"], "2026-03-20")
        self.assertEqual(result["mode"], "backfill")

    def test_incremental_mode_ignores_explicit_date_range(self):
        self.settings.update_settings(
            "market_data",
            [
                {"key": "start_date", "value": "2026-03-01", "is_secret": False},
                {"key": "end_date", "value": "2026-03-20", "is_secret": False},
            ],
        )

        with patch("backend.services.market_data_service.TushareAPI", _FakeTushareAPI):
            result = self.service.sync_configured_data(mode="incremental")

        self.assertNotEqual(result["range_start"], "2026-03-01")
        self.assertNotEqual(result["range_end"], "2026-03-20")
        self.assertEqual(result["mode"], "incremental")

    def test_sync_configured_data_collects_partial_failures(self):
        with patch("backend.services.market_data_service.TushareAPI", _PartiallyFailingTushareAPI):
            result = self.service.sync_configured_data()

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("600519.SH", result["errors"][0])

    def test_search_stock_candidates_supports_query_and_multi_filters(self):
        with patch("backend.services.market_data_service.TushareAPI", _FakeTushareAPI):
            result = self.service.search_stock_candidates(
                query="中芯",
                market="科创板",
                area="上海",
                industry="半导体",
                limit=10,
            )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["ts_code"], "688981.SH")
        self.assertIn("科创板", result["markets"])
        self.assertIn("上海", result["areas"])
        self.assertIn("半导体", result["industries"])

    def test_sync_configured_data_rejects_invalid_symbols(self):
        self.settings.update_settings(
            "market_data",
            [
                {"key": "symbols", "value": "ABC123", "is_secret": False},
            ],
        )

        with self.assertRaisesRegex(ValueError, "股票代码格式不正确"):
            self.service.sync_configured_data()

    def test_backfill_rejects_future_date_range(self):
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        self.settings.update_settings(
            "market_data",
            [
                {"key": "start_date", "value": start_date, "is_secret": False},
                {"key": "end_date", "value": tomorrow, "is_secret": False},
            ],
        )

        with self.assertRaisesRegex(ValueError, "不能晚于今天"):
            self.service.sync_configured_data(mode="backfill")
