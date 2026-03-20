import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.factory import LLMFactory
from src.llm.base import BaseLLM


class DummyLLM(BaseLLM):
    def chat(self, messages, **kwargs):
        return "ok"

    def chat_with_tools(self, messages, tools, **kwargs):
        return {"content": "ok", "tool_calls": []}


class TestLLMFactory(unittest.TestCase):
    """测试LLM工厂"""

    def test_create_openai_adapter(self):
        """测试创建OpenAI适配器"""
        with patch("src.llm.factory.OpenAIAdapter", return_value=DummyLLM()):
            llm = LLMFactory.create(
                "openai",
                api_key="test-key",
                api_base="https://api.openai.com/v1",
                model="gpt-4"
            )
        self.assertIsInstance(llm, BaseLLM)

    def test_create_anthropic_adapter(self):
        """测试创建Anthropic适配器"""
        with patch("src.llm.factory.AnthropicAdapter", return_value=DummyLLM()):
            llm = LLMFactory.create(
                "anthropic",
                api_key="test-key",
                model="claude-3-opus-20240229"
            )
        self.assertIsInstance(llm, BaseLLM)

    def test_unsupported_provider(self):
        """测试不支持的提供商"""
        with self.assertRaises(ValueError):
            LLMFactory.create("unsupported", api_key="test")


if __name__ == '__main__':
    unittest.main()
