import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.adapters import OpenAIAdapter


class TestOpenAIAdapter(unittest.TestCase):
    def _mock_openai_module(self, client):
        fake_module = types.ModuleType("openai")
        fake_module.OpenAI = MagicMock(return_value=client)
        return fake_module

    def test_normalize_base_url_appends_v1_for_root_url(self):
        self.assertEqual(
            OpenAIAdapter._normalize_base_url("https://example.com/"),
            "https://example.com/v1",
        )
        self.assertEqual(
            OpenAIAdapter._normalize_base_url("https://example.com/v1"),
            "https://example.com/v1",
        )

    def test_chat_returns_plain_string_content(self):
        message = SimpleNamespace(content="ok")
        response = SimpleNamespace(choices=[SimpleNamespace(message=message)])
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=MagicMock(return_value=response))
            )
        )

        with patch.dict(sys.modules, {"openai": self._mock_openai_module(client)}):
            adapter = OpenAIAdapter(
                api_key="test-key",
                api_base="https://example.com/",
                model="gpt-4",
            )
            result = adapter.chat([{"role": "user", "content": "ping"}])

        self.assertEqual(result, "ok")
        client.chat.completions.create.assert_called_once()

    def test_chat_joins_structured_content_parts(self):
        content = [
            {"type": "text", "text": "hello "},
            SimpleNamespace(type="text", text="world"),
        ]
        message = SimpleNamespace(content=content)
        response = SimpleNamespace(choices=[SimpleNamespace(message=message)])
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=MagicMock(return_value=response))
            )
        )

        with patch.dict(sys.modules, {"openai": self._mock_openai_module(client)}):
            adapter = OpenAIAdapter(
                api_key="test-key",
                api_base="https://example.com/v1",
                model="gpt-4",
            )
            result = adapter.chat([{"role": "user", "content": "ping"}])

        self.assertEqual(result, "hello world")
