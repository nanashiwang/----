import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtest.portfolio_engine import PortfolioBacktestEngine
from src.data.db.sqlite_client import SQLiteClient
from src.ml.dataset_builder import DatasetBuilder
from src.ml.selector import FeatureSelector
from src.ml.trainer import sklearn_runtime_available


class TestPortfolioBacktestEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = SQLiteClient(str(Path(self.temp_dir.name) / "portfolio.db"))
        self.symbols = ["000001.SZ", "600519.SH", "300750.SZ"]
        self._seed_market_data()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _seed_market_data(self):
        business_days = pd.bdate_range("2025-09-01", periods=170)
        symbol_profile = {
            "000001.SZ": {"base": 10.0, "trend": 0.18, "pe_base": 11.0, "flow_sign": 1.0},
            "600519.SH": {"base": 16.0, "trend": 0.08, "pe_base": 18.0, "flow_sign": 0.4},
            "300750.SZ": {"base": 12.0, "trend": -0.06, "pe_base": 28.0, "flow_sign": -0.6},
        }

        with self.db.get_connection() as conn:
            for index, trade_date in enumerate(business_days):
                trade_date_str = trade_date.strftime("%Y-%m-%d")
                for symbol, profile in symbol_profile.items():
                    cycle = ((index % 6) - 2) * 0.03
                    close_price = profile["base"] + profile["trend"] * index + cycle
                    open_price = close_price * (0.995 if profile["trend"] >= 0 else 1.005)
                    high_price = max(open_price, close_price) * 1.01
                    low_price = min(open_price, close_price) * 0.99
                    volume = 120000 + index * 650 + abs(profile["trend"]) * 10000
                    amount = volume * close_price / 10

                    conn.execute(
                        """
                        INSERT INTO stock_data (ts_code, trade_date, open, close, high, low, volume, amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            symbol,
                            trade_date_str,
                            open_price,
                            close_price,
                            high_price,
                            low_price,
                            volume,
                            amount,
                        ),
                    )

                    daily_basic_metrics = {
                        "turnover_rate": 1.5 + index * 0.01 + abs(profile["trend"]),
                        "volume_ratio": 1.0 + profile["trend"],
                        "pe": profile["pe_base"] - profile["trend"] * 10,
                        "pb": 2.0 + abs(profile["trend"]) * 5,
                    }
                    conn.execute(
                        """
                        INSERT INTO market_data_snapshots (ts_code, trade_date, dataset, metrics_json)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            symbol,
                            trade_date_str,
                            "daily_basic",
                            json.dumps(daily_basic_metrics, ensure_ascii=False),
                        ),
                    )

                    moneyflow_metrics = {
                        "buy_lg_amount": amount * 0.15,
                        "sell_lg_amount": amount * 0.12,
                        "net_mf_amount": amount * profile["flow_sign"] * 0.08,
                        "net_mf_vol": volume * profile["flow_sign"] * 0.05,
                    }
                    conn.execute(
                        """
                        INSERT INTO market_data_snapshots (ts_code, trade_date, dataset, metrics_json)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            symbol,
                            trade_date_str,
                            "moneyflow",
                            json.dumps(moneyflow_metrics, ensure_ascii=False),
                        ),
                    )

                    if index % 12 == 0 and profile["trend"] > 0:
                        top_list_metrics = {
                            "reason": "机构席位活跃",
                            "net_amount": amount * 0.06,
                        }
                        conn.execute(
                            """
                            INSERT INTO market_data_snapshots (ts_code, trade_date, dataset, metrics_json)
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                symbol,
                                trade_date_str,
                                "top_list",
                                json.dumps(top_list_metrics, ensure_ascii=False),
                            ),
                        )

            conn.commit()

    def test_dataset_builder_and_selector_build_ml_samples(self):
        builder = DatasetBuilder(self.db)
        dataset = builder.build_dataset(
            symbols=self.symbols,
            query_start_date="2025-09-01",
            query_end_date="2026-03-31",
            signal_start_date="2025-11-01",
            signal_end_date="2026-03-20",
            hold_days=5,
        )

        self.assertFalse(dataset.empty)
        self.assertIn("future_return", dataset.columns)
        self.assertIn("future_excess_return", dataset.columns)
        self.assertIn("ma20_bias", dataset.columns)
        self.assertIn("net_mf_ratio", dataset.columns)

        train_df = dataset[dataset["sell_date"] < pd.Timestamp("2026-02-03")]
        selection = FeatureSelector().select(train_df, top_k=4)
        self.assertTrue(selection["selected_features"])
        self.assertGreaterEqual(len(selection["feature_stats"]), len(selection["selected_features"]))

    def test_run_factor_backtest_returns_standard_metrics(self):
        engine = PortfolioBacktestEngine(self.db)
        result = engine.run_factor_backtest(
            start_date="2026-02-03",
            end_date="2026-03-20",
            symbols=self.symbols,
            hold_days=5,
            top_n=2,
            train_window_days=70,
            max_features=4,
        )

        self.assertEqual(result["mode"], "portfolio")
        self.assertTrue(result["selected_features"])
        self.assertTrue(result["model_weights"])
        self.assertTrue(result["equity_curve"])
        self.assertTrue(result["trades"])
        self.assertGreater(result["summary"]["trade_count"], 0)
        self.assertIn("cumulative_return", result["summary"])
        self.assertIn("max_drawdown", result["summary"])
        self.assertIn("turnover_rate", result["summary"])

    @unittest.skipUnless(sklearn_runtime_available(), "当前测试环境的 sklearn/scipy/numpy 组合不兼容")
    def test_run_factor_backtest_supports_sklearn_ridge(self):
        engine = PortfolioBacktestEngine(self.db)
        result = engine.run_factor_backtest(
            start_date="2026-02-03",
            end_date="2026-03-20",
            symbols=self.symbols,
            hold_days=5,
            top_n=2,
            train_window_days=70,
            max_features=4,
            model_type="sklearn_ridge",
        )

        self.assertEqual(result["mode"], "portfolio")
        self.assertEqual(result["model_type"], "sklearn_ridge")
        self.assertTrue(result["model_weights"])
        self.assertIn("train_score", result["training_summary"])
        self.assertGreater(result["summary"]["trade_count"], 0)

    @unittest.skipUnless(sklearn_runtime_available(), "当前测试环境的 sklearn/scipy/numpy 组合不兼容")
    def test_run_factor_backtest_supports_compare_mode(self):
        engine = PortfolioBacktestEngine(self.db)
        result = engine.run_factor_backtest(
            start_date="2026-02-03",
            end_date="2026-03-20",
            symbols=self.symbols,
            hold_days=5,
            top_n=2,
            train_window_days=70,
            max_features=4,
            model_type="compare",
        )

        self.assertEqual(result["mode"], "portfolio")
        self.assertEqual(result["model_type"], "compare")
        self.assertEqual(len(result["experiments"]), 2)
        self.assertEqual(
            {item["model_type"] for item in result["experiments"]},
            {"linear_factor", "sklearn_ridge"},
        )
        self.assertIn("winner", result["comparison_summary"])


if __name__ == "__main__":
    unittest.main()
