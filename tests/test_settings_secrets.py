import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.routers.settings import _resolve_secret_value


class _DummyService:
    def __init__(self, raw_value):
        self.raw_value = raw_value

    def get_raw_value(self, category, key):
        return self.raw_value


class TestSettingsSecrets(unittest.TestCase):
    """测试设置页密钥回退逻辑"""

    def test_resolve_secret_value_returns_submitted_plain_value(self):
        service = _DummyService("stored-secret")
        self.assertEqual(
            _resolve_secret_value(service, "llm", "api_key", "sk-live-secret"),
            "sk-live-secret",
        )

    def test_resolve_secret_value_falls_back_for_masked_value(self):
        service = _DummyService("stored-secret")
        self.assertEqual(
            _resolve_secret_value(service, "llm", "api_key", "sk-li****cret"),
            "stored-secret",
        )

    def test_resolve_secret_value_falls_back_for_empty_value(self):
        service = _DummyService("stored-secret")
        self.assertEqual(
            _resolve_secret_value(service, "llm", "api_key", ""),
            "stored-secret",
        )
