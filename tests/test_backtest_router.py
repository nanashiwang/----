import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-backtest-router"

import backend.app as backend_app_module
from backend.auth.jwt_handler import create_access_token
from backend.services.settings_service import SettingsService
from src.data.db.sqlite_client import SQLiteClient


class TestBacktestRouter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = SQLiteClient(str(Path(self.temp_dir.name) / "backtest-router.db"))
        self.settings = SettingsService(self.db)
        self.original_sqlite_client = backend_app_module._sqlite_client
        backend_app_module._sqlite_client = self.db

    def tearDown(self):
        backend_app_module._sqlite_client = self.original_sqlite_client
        self.temp_dir.cleanup()

    def _auth_headers(self):
        token = create_access_token({"sub": "admin", "role": "admin", "uid": 1})
        return {"Authorization": f"Bearer {token}"}

    def test_portfolio_mode_dispatches_to_standard_engine(self):
        with patch(
            "backend.routers.backtest.PortfolioBacktestEngine.run_factor_backtest",
            return_value={
                "mode": "portfolio",
                "model_type": "sklearn_ridge",
                "summary": {"trade_count": 6},
                "selected_features": ["momentum_10d"],
                "model_weights": [{"feature": "momentum_10d", "weight": 1.0}],
                "equity_curve": [],
                "trades": [],
                "training_summary": {"train_samples": 120, "test_samples": 40},
            },
        ) as mock_run:
            with TestClient(backend_app_module.app) as client:
                response = client.post(
                    "/api/backtest",
                    headers=self._auth_headers(),
                    params={
                        "mode": "portfolio",
                        "model_type": "sklearn_ridge",
                        "start_date": "2026-02-01",
                        "end_date": "2026-03-20",
                        "hold_days": 5,
                        "top_n": 3,
                        "train_window_days": 120,
                        "max_features": 5,
                        "symbols": "000001.SZ,600519.SH",
                    },
                )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["mode"], "portfolio")
        self.assertEqual(body["summary"]["trade_count"], 6)
        mock_run.assert_called_once()
        kwargs = mock_run.call_args.kwargs
        self.assertEqual(kwargs["symbols"], ["000001.SZ", "600519.SH"])
        self.assertEqual(kwargs["top_n"], 3)
        self.assertEqual(kwargs["max_features"], 5)
        self.assertEqual(kwargs["model_type"], "sklearn_ridge")
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM usage_logs ORDER BY id DESC LIMIT 1").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["module"], "backtest")
        self.assertEqual(row["method"], "sklearn_ridge")
        self.assertEqual(row["status"], "success")

    def test_portfolio_compare_mode_dispatches_with_compare_flag(self):
        with patch(
            "backend.routers.backtest.PortfolioBacktestEngine.run_factor_backtest",
            return_value={
                "mode": "portfolio",
                "model_type": "compare",
                "experiments": [],
                "comparison_summary": {"winner": "sklearn_ridge"},
            },
        ) as mock_run:
            with TestClient(backend_app_module.app) as client:
                response = client.post(
                    "/api/backtest",
                    headers=self._auth_headers(),
                    params={
                        "mode": "portfolio",
                        "model_type": "compare",
                        "start_date": "2026-02-01",
                        "end_date": "2026-03-20",
                    },
                )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["model_type"], "compare")
        self.assertEqual(mock_run.call_args.kwargs["model_type"], "compare")

    def test_review_mode_keeps_legacy_entry(self):
        self.settings.update_settings(
            "tushare",
            [
                {"key": "token", "value": "demo-token", "is_secret": True},
                {"key": "api_url", "value": "http://127.0.0.1:8010/", "is_secret": False},
            ],
        )

        with patch("backend.routers.backtest.TushareAPI") as mock_api, patch(
            "backend.routers.backtest.BacktestEngine"
        ) as mock_engine_cls:
            mock_engine_cls.return_value.run_backtest.return_value = {
                "total_trades": 3,
                "win_rate": 0.67,
                "avg_return": 0.08,
                "max_return": 0.12,
                "details": [],
            }
            with TestClient(backend_app_module.app) as client:
                response = client.post(
                    "/api/backtest",
                    headers=self._auth_headers(),
                    params={
                        "mode": "review",
                        "start_date": "2026-02-01",
                        "end_date": "2026-03-20",
                        "hold_days": 7,
                    },
                )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["mode"], "review")
        self.assertEqual(body["total_trades"], 3)
        mock_api.assert_called_once_with("demo-token", api_url="http://127.0.0.1:8010/")
        mock_engine_cls.return_value.run_backtest.assert_called_once_with("2026-02-01", "2026-03-20", 7)
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM usage_logs ORDER BY id DESC LIMIT 1").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["action"], "review_backtest")
        self.assertEqual(row["method"], "review / hold_7d")


if __name__ == "__main__":
    unittest.main()
