import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.settings_service import SettingsService
from src.data.db.sqlite_client import SQLiteClient


class TestSettingsService(unittest.TestCase):
    """测试系统配置服务"""

    def test_update_settings_keeps_existing_secret_when_value_is_masked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db = SQLiteClient(str(db_path))
            service = SettingsService(db)

            service.update_settings("llm", [
                {"key": "api_key", "value": "sk-real-secret-value", "is_secret": True}
            ], user_id=1)

            service.update_settings("llm", [
                {"key": "api_key", "value": "sk-r****alue", "is_secret": True}
            ], user_id=1)

            self.assertEqual(
                service.get_raw_value("llm", "api_key"),
                "sk-real-secret-value",
            )
