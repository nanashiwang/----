from typing import List, Dict, Any
from .base import BaseLLM


class OpenAIAdapter(BaseLLM):
    def __init__(self, api_key: str, api_base: str, model: str, **kwargs):
        from langchain_openai import ChatOpenAI
        self.llm = ChatOpenAI(
            api_key=api_key,
            base_url=api_base,
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
