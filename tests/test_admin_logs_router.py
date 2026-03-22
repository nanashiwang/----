import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-admin-logs-router"

import backend.app as backend_app_module
from backend.auth.jwt_handler import create_access_token
from backend.services.usage_log_service import UsageLogService
from src.data.db.sqlite_client import SQLiteClient


class TestAdminLogsRouter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = SQLiteClient(str(Path(self.temp_dir.name) / "admin-logs-router.db"))
        self.original_sqlite_client = backend_app_module._sqlite_client
        backend_app_module._sqlite_client = self.db
        self.log_service = UsageLogService(self.db)
        self.log_service.record_backtest_run(
            {"uid": 1, "sub": "alice", "role": "user"},
            mode="portfolio",
            model_type="linear_factor",
            start_date="2026-02-01",
            end_date="2026-03-20",
            hold_days=5,
            top_n=5,
            train_window_days=120,
            max_features=6,
            symbols=["000001.SZ", "600519.SH"],
            result={
                "mode": "portfolio",
                "summary": {
                    "annualized_excess_return": 0.12,
                    "cumulative_return": 0.18,
                    "win_rate": 0.62,
                },
                "training_summary": {"train_samples": 120},
                "selected_features": ["momentum_10d"],
            },
        )

    def tearDown(self):
        backend_app_module._sqlite_client = self.original_sqlite_client
        self.temp_dir.cleanup()

    def _headers(self, role: str):
        token = create_access_token({"sub": f"{role}-tester", "role": role, "uid": 99})
        return {"Authorization": f"Bearer {token}"}

    def test_admin_can_list_usage_logs(self):
        with TestClient(backend_app_module.app) as client:
            response = client.get("/api/admin/logs", headers=self._headers("admin"))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["summary"]["total_runs"], 1)
        self.assertEqual(body["items"][0]["username"], "alice")
        self.assertEqual(body["items"][0]["module"], "backtest")
        self.assertEqual(body["items"][0]["primary_metric_name"], "annualized_excess_return")

    def test_non_admin_cannot_list_usage_logs(self):
        with TestClient(backend_app_module.app) as client:
            response = client.get("/api/admin/logs", headers=self._headers("user"))

        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()

