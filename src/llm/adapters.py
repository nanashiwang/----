from typing import List, Dict, Any
from urllib.parse import urlparse
from .base import BaseLLM


class OpenAIAdapter(BaseLLM):
    def __init__(self, api_key: str, api_base: str, model: str, **kwargs):
        from openai import OpenAI

        self.model = model
        self.default_kwargs = kwargs
        self.client = OpenAI(
            api_key=api_key,
            base_url=self._normalize_base_url(api_base),
        )

    @staticmethod
    def _normalize_base_url(api_base: str | None) -> str | None:
        if not api_base:
            return api_base

        normalized = api_base.rstrip("/")
        parsed = urlparse(normalized)
        if parsed.path in ("", "/"):
            return f"{normalized}/v1"
        return normalized

    @staticmethod
    def _extract_text_content(content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if isinstance(item, dict):
                    if item.get("type") == "text" and item.get("text"):
                        parts.append(item["text"])
                    elif item.get("content"):
                        parts.append(str(item["content"]))
                    continue

                item_type = getattr(item, "type", None)
                text = getattr(item, "text", None)
                if item_type == "text" and text:
                    parts.append(text)
                elif text:
                    parts.append(str(text))
            return "".join(parts)
        return str(content)

    @staticmethod
    def _normalize_tool_calls(tool_calls: Any) -> List[Dict[str, Any]]:
        normalized_calls: List[Dict[str, Any]] = []
        for tool_call in tool_calls or []:
            if isinstance(tool_call, dict):
                normalized_calls.append(tool_call)
                continue

            function = getattr(tool_call, "function", None)
            normalized_calls.append({
                "id": getattr(tool_call, "id", None),
                "type": getattr(tool_call, "type", "function"),
                "function": {
                    "name": getattr(function, "name", None),
                    "arguments": getattr(function, "arguments", None),
                } if function else None,
            })
        return normalized_calls

    def _build_request_kwargs(self, **kwargs) -> Dict[str, Any]:
        request_kwargs = {
            "model": kwargs.pop("model", self.model),
            "messages": kwargs.pop("messages"),
            "temperature": kwargs.pop("temperature", self.default_kwargs.get("temperature", 0.7)),
        }

        max_tokens = kwargs.pop("max_tokens", self.default_kwargs.get("max_tokens"))
        if max_tokens is not None:
            request_kwargs["max_tokens"] = max_tokens

        request_kwargs.update(kwargs)
        return request_kwargs

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        response = self.client.chat.completions.create(
            **self._build_request_kwargs(messages=messages, **kwargs)
        )
        message = response.choices[0].message
        return self._extract_text_content(getattr(message, "content", ""))

    def chat_with_tools(self, messages: List[Dict[str, str]],
                       tools: List[Dict], **kwargs) -> Dict[str, Any]:
        response = self.client.chat.completions.create(
            **self._build_request_kwargs(messages=messages, tools=tools, **kwargs)
        )
        message = response.choices[0].message
        return {
            "content": self._extract_text_content(getattr(message, "content", "")),
            "tool_calls": self._normalize_tool_calls(getattr(message, "tool_calls", [])),
        }


class AnthropicAdapter(BaseLLM):
    def __init__(self, api_key: str, model: str, **kwargs):
        from langchain_anthropic import ChatAnthropic
        self.llm = ChatAnthropic(
            api_key=api_key,
            model=model,
            **kwargs
        )

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

        lc_messages = []
        for msg in messages:
            if msg["role"] == "system":
                lc_messages.append(SystemMessage(content=msg["content"]))
            elif msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))

        response = self.llm.invoke(lc_messages)
        return response.content

    def chat_with_tools(self, messages: List[Dict[str, str]],
                       tools: List[Dict], **kwargs) -> Dict[str, Any]:
        llm_with_tools = self.llm.bind_tools(tools)
        response = llm_with_tools.invoke(messages)
        return {
            "content": response.content,
            "tool_calls": response.tool_calls if hasattr(response, "tool_calls") else []
        }
