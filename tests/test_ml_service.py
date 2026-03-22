import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models.ml import MlExperimentRequest
from backend.services.ml_service import MLExperimentService
from src.data.db.sqlite_client import SQLiteClient
from src.ml.trainer import sklearn_runtime_available


class TestMLExperimentService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = SQLiteClient(str(Path(self.temp_dir.name) / "ml-service.db"))
        self.symbols = ["000001.SZ", "600519.SH", "300750.SZ"]
        self._seed_market_data()
        self.service = MLExperimentService(self.db)

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
                benchmark_close = 3800 + index * 2.4 + ((index % 8) - 3) * 3.2
                benchmark_open = benchmark_close * 0.998
                benchmark_high = benchmark_close * 1.006
                benchmark_low = benchmark_close * 0.994
                benchmark_pre_close = benchmark_close - 8
                benchmark_change = benchmark_close - benchmark_pre_close
                benchmark_pct_chg = benchmark_change / benchmark_pre_close * 100
                benchmark_volume = 180000000 + index * 120000
                benchmark_amount = benchmark_volume * benchmark_close / 100

                conn.execute(
                    """
                    INSERT INTO market_index_data (
                        index_code, trade_date, open, close, high, low, pre_close,
                        change, pct_chg, volume, amount
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "000300.SH",
                        trade_date_str,
                        benchmark_open,
                        benchmark_close,
                        benchmark_high,
                        benchmark_low,
                        benchmark_pre_close,
                        benchmark_change,
                        benchmark_pct_chg,
                        benchmark_volume,
                        benchmark_amount,
                    ),
                )

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

    def test_get_options_returns_feature_model_and_date_metadata(self):
        result = self.service.get_options()

        self.assertEqual(result["cycle"], "daily")
        self.assertTrue(result["symbols"])
        self.assertTrue(result["feature_options"])
        self.assertTrue(result["label_options"])
        self.assertTrue(result["model_options"])
        self.assertEqual(result["date_bounds"]["min_date"], "2025-09-01")

    def test_run_experiment_with_linear_factor_returns_predictions(self):
        payload = MlExperimentRequest(
            symbols=self.symbols,
            feature_columns=["momentum_10d", "ma20_bias", "net_mf_ratio", "top_list_flag"],
            label_column="future_excess_return",
            model_type="linear_factor",
            tuning_method="none",
            train_start_date="2025-11-01",
            train_end_date="2026-02-10",
            predict_start_date="2026-02-11",
            predict_end_date="2026-03-20",
            hold_days=5,
            use_feature_selection=True,
            max_features=3,
            prediction_top_n=2,
            tuning_trials=10,
        )

        result = self.service.run_experiment(payload)

        self.assertEqual(result["cycle"], "daily")
        self.assertTrue(result["selected_features"])
        self.assertTrue(result["feature_stats"])
        self.assertTrue(result["predictions"])
        self.assertGreater(result["sample_summary"]["train_samples"], 0)
        self.assertEqual(result["tuning_summary"]["method"], "none")

    def test_run_experiment_supports_benchmark_relative_label(self):
        payload = MlExperimentRequest(
            symbols=self.symbols,
            feature_columns=["relative_strength_5d", "benchmark_return_5d", "excess_momentum_20d", "net_mf_ratio"],
            label_column="future_benchmark_excess_return",
            model_type="linear_factor",
            tuning_method="none",
            train_start_date="2025-11-01",
            train_end_date="2026-02-10",
            predict_start_date="2026-02-11",
            predict_end_date="2026-03-20",
            hold_days=5,
            use_feature_selection=False,
            max_features=4,
            prediction_top_n=2,
            tuning_trials=10,
        )

        result = self.service.run_experiment(payload)

        self.assertEqual(result["params"]["label_column"], "future_benchmark_excess_return")
        self.assertIn("benchmark_return_5d", result["selected_features"])
        self.assertTrue(result["predictions"])
        self.assertGreater(result["sample_summary"]["train_samples"], 0)

    @unittest.skipUnless(sklearn_runtime_available(), "当前测试环境的 sklearn 运行时不可用")
    def test_run_experiment_supports_grid_search_for_ridge(self):
        payload = MlExperimentRequest(
            symbols=self.symbols,
            feature_columns=["momentum_10d", "ma20_bias", "net_mf_ratio", "turnover_rate"],
            label_column="future_excess_return",
            model_type="sklearn_ridge",
            tuning_method="grid_search",
            train_start_date="2025-11-01",
            train_end_date="2026-02-10",
            predict_start_date="2026-02-11",
            predict_end_date="2026-03-20",
            hold_days=5,
            use_feature_selection=False,
            max_features=4,
            prediction_top_n=2,
            tuning_trials=10,
        )

        result = self.service.run_experiment(payload)

        self.assertEqual(result["tuning_summary"]["method"], "grid_search")
        self.assertTrue(result["tuning_summary"]["history"])
        self.assertIn("alpha", result["tuning_summary"]["best_params"])
        self.assertTrue(result["predictions"])
