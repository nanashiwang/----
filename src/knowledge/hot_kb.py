from typing import List, Dict, Optional
from datetime import datetime
from ..data.db.mongo_client import MongoDBClient


class HotKnowledgeBase:
    """热知识库管理"""

    def __init__(self, mongo_client: MongoDBClient):
        self.mongo = mongo_client

    def add_experience(self, content: str, category: str) -> str:
        """添加新经验到热知识库"""
        return self.mongo.add_hot_knowledge(content, category)

    def test_experience(self, exp_id: str, success: bool):
        """测试经验并更新统计"""
        self.mongo.update_knowledge_test(exp_id, success)

    def get_top_experiences(self, limit: int = 10) -> List[Dict]:
        """获取置信度最高的经验"""
        return self.mongo.get_top_hot_knowledge(limit)

    def promote_to_cold(self, exp_id: str, agent_name: str, threshold: float = 0.7, min_tests: int = 10):
        """将高质量经验沉淀到冷知识库"""
        from bson import ObjectId
        collection = self.mongo.get_collection("hot_knowledge")
        exp = collection.find_one({"_id": ObjectId(exp_id)})

        if exp and exp["test_count"] >= min_tests and exp["confidence"] >= threshold:
            self.mongo.save_cold_knowledge(agent_name, exp["content"], from_hot=True)
            return True
        return False
