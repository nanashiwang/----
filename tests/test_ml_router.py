import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-ml-router"

import backend.app as backend_app_module
from backend.auth.jwt_handler import create_access_token
from src.data.db.sqlite_client import SQLiteClient


class TestMLRouter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = SQLiteClient(str(Path(self.temp_dir.name) / "ml-router.db"))
        self.original_sqlite_client = backend_app_module._sqlite_client
        backend_app_module._sqlite_client = self.db

    def tearDown(self):
        backend_app_module._sqlite_client = self.original_sqlite_client
        self.temp_dir.cleanup()

    def _auth_headers(self):
        token = create_access_token({"sub": "tester", "role": "user", "uid": 1})
        return {"Authorization": f"Bearer {token}"}

    def test_get_ml_options(self):
        with patch(
            "backend.routers.ml.MLExperimentService.get_options",
            return_value={
                "cycle": "daily",
                "cycle_label": "日线同周期",
                "date_bounds": {"min_date": "2025-01-01", "max_date": "2026-03-20"},
                "symbols": ["000001.SZ"],
                "feature_options": [{"value": "momentum_10d", "label": "10日动量"}],
                "label_options": [{"value": "future_excess_return", "label": "未来超额收益率"}],
                "model_options": [{"value": "linear_factor", "label": "线性因子评分"}],
                "tuning_options": [{"value": "none", "label": "不调优"}],
                "defaults": {"model_type": "linear_factor"},
                "runtime": {"sklearn_available": True, "optuna_available": False},
            },
        ):
            with TestClient(backend_app_module.app) as client:
                response = client.get("/api/ml/options", headers=self._auth_headers())

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["cycle"], "daily")
        self.assertEqual(body["symbols"], ["000001.SZ"])

    def test_run_ml_experiment(self):
        with patch(
            "backend.routers.ml.MLExperimentService.run_experiment",
            return_value={
                "cycle": "daily",
                "params": {"model_type": "linear_factor"},
                "sample_summary": {"train_samples": 120, "prediction_samples": 20},
                "selected_features": ["momentum_10d"],
                "feature_stats": [{"feature": "momentum_10d", "ic": 0.2}],
                "model_weights": [{"feature": "momentum_10d", "weight": 1.0}],
                "training_summary": {"train_score": 0.0},
                "tuning_summary": {"method": "none"},
                "prediction_summary": {"row_count": 10},
                "predictions": [{"trade_date": "2026-03-20", "ts_code": "000001.SZ"}],
            },
        ) as mock_run:
            with TestClient(backend_app_module.app) as client:
                response = client.post(
                    "/api/ml/experiments/run",
                    headers=self._auth_headers(),
                    json={
                        "symbols": ["000001.SZ"],
                        "feature_columns": ["momentum_10d"],
                        "label_column": "future_excess_return",
                        "model_type": "linear_factor",
                        "tuning_method": "none",
                        "train_start_date": "2025-11-01",
                        "train_end_date": "2026-02-10",
                        "predict_start_date": "2026-02-11",
                        "predict_end_date": "2026-03-20",
                        "hold_days": 5,
                        "use_feature_selection": True,
                        "max_features": 3,
                        "prediction_top_n": 2,
                        "tuning_trials": 10,
                    },
                )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["cycle"], "daily")
        self.assertEqual(body["prediction_summary"]["row_count"], 10)
        mock_run.assert_called_once()
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM usage_logs ORDER BY id DESC LIMIT 1").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["module"], "ml")
        self.assertEqual(row["method"], "linear_factor")
        self.assertEqual(row["status"], "success")
