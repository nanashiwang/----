from typing import Dict, Any
from .base import BaseLLM
from .adapters import OpenAIAdapter, AnthropicAdapter


class LLMFactory:
    @staticmethod
    def create(provider: str, **config) -> BaseLLM:
        if provider == "openai" or provider == "custom":
            return OpenAIAdapter(
                api_key=config.get("api_key"),
                api_base=config.get("api_base"),
                model=config.get("model"),
                temperature=config.get("temperature", 0.7),
                max_tokens=config.get("max_tokens", 2000)
            )
        elif provider == "anthropic":
            return AnthropicAdapter(
                api_key=config.get("api_key"),
                model=config.get("model"),
                temperature=config.get("temperature", 0.7),
                max_tokens=config.get("max_tokens", 2000)
            )
        else:
            raise ValueError(f"不支持的LLM提供商: {provider}")
