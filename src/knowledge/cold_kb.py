from typing import List, Dict
from ..data.db.mongo_client import MongoDBClient


class ColdKnowledgeBase:
    """冷知识库管理"""

    def __init__(self, mongo_client: MongoDBClient):
        self.mongo = mongo_client

    def save_experience(self, agent_name: str, content: str):
        """保存经验到冷知识库"""
        self.mongo.save_cold_knowledge(agent_name, content, from_hot=False)

    def load_agent_knowledge(self, agent_name: str) -> List[Dict]:
        """加载特定Agent的冷知识库"""
        return self.mongo.get_agent_cold_knowledge(agent_name)

    def format_for_prompt(self, agent_name: str) -> str:
        """格式化知识库内容用于Prompt注入"""
        knowledge = self.load_agent_knowledge(agent_name)
        if not knowledge:
            return ""

        formatted = "## 历史经验知识库\n\n"
        for idx, exp in enumerate(knowledge, 1):
            formatted += f"{idx}. {exp['content']}\n"

        return formatted
