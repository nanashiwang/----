from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseLLM(ABC):
    """LLM基类"""

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """基础对话接口"""
        pass

    @abstractmethod
    def chat_with_tools(self, messages: List[Dict[str, str]],
                       tools: List[Dict], **kwargs) -> Dict[str, Any]:
        """带工具调用的对话接口"""
        pass
