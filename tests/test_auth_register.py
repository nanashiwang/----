import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-register-tests"

import backend.app as backend_app_module
from src.data.db.sqlite_client import SQLiteClient


class TestAuthRegister(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "register.db"
        self.db = SQLiteClient(str(db_path))
        self.original_sqlite_client = backend_app_module._sqlite_client
        backend_app_module._sqlite_client = self.db

    def tearDown(self):
        backend_app_module._sqlite_client = self.original_sqlite_client
        self.temp_dir.cleanup()

    def test_register_creates_user_and_login_works(self):
        with TestClient(backend_app_module.app) as client:
            register_response = client.post(
                "/api/auth/register",
                json={"username": "new-user", "password": "new-password-123"},
            )
            login_response = client.post(
                "/api/auth/login",
                json={"username": "new-user", "password": "new-password-123"},
            )

        self.assertEqual(register_response.status_code, 200)
        self.assertEqual(register_response.json()["username"], "new-user")
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.json()["access_token"])

    def test_register_rejects_duplicate_username(self):
        with TestClient(backend_app_module.app) as client:
            first = client.post(
                "/api/auth/register",
                json={"username": "duplicate-user", "password": "new-password-123"},
            )
            second = client.post(
                "/api/auth/register",
                json={"username": "duplicate-user", "password": "another-password-123"},
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertIn("用户名已存在", second.json()["detail"])

    def test_register_trims_username(self):
        with TestClient(backend_app_module.app) as client:
            response = client.post(
                "/api/auth/register",
                json={"username": "  trader-one  ", "password": "new-password-123"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "trader-one")

    def test_register_rejects_short_password(self):
        with TestClient(backend_app_module.app) as client:
            response = client.post(
                "/api/auth/register",
                json={"username": "short-pass-user", "password": "123"},
            )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
