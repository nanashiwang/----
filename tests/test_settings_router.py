import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.routers.settings import (
    _normalize_api_base,
    _should_use_responses_test,
    _test_responses_stream,
)


class _FakeResponse:
    def __init__(self, lines):
        self._lines = lines

    def raise_for_status(self):
        return None

    def iter_lines(self, decode_unicode=False):
        for line in self._lines:
            yield line if decode_unicode else line.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestSettingsRouterHelpers(unittest.TestCase):
    """测试设置路由辅助逻辑"""

    def test_normalize_api_base_appends_v1_for_root_url(self):
        self.assertEqual(_normalize_api_base("https://example.com/"), "https://example.com/v1")
        self.assertEqual(_normalize_api_base("https://example.com/v1"), "https://example.com/v1")

    def test_should_use_responses_test_for_codex_models(self):
        self.assertTrue(_should_use_responses_test("openai", "gpt-5.2-codex"))
        self.assertTrue(_should_use_responses_test("custom", "gpt-5"))
        self.assertFalse(_should_use_responses_test("openai", "gpt-4"))

    def test_test_responses_stream_returns_success_after_first_event(self):
        fake_response = _FakeResponse(["event: response.created", "data: {}"])

        with patch("backend.routers.settings.requests.post", return_value=fake_response) as mock_post:
            result = _test_responses_stream("https://example.com/", "test-key", "gpt-5.2-codex")

        self.assertTrue(result["success"])
        self.assertIn("response.created", result["message"])
        mock_post.assert_called_once()
