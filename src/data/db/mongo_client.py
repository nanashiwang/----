from pymongo import MongoClient
from typing import Optional, Dict, Any, List
from datetime import datetime


class MongoDBClient:
    def __init__(self, uri: str, db_name: str):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

    def get_collection(self, name: str):
        return self.db[name]

    # 热知识库操作
    def add_hot_knowledge(self, content: str, category: str) -> str:
        collection = self.get_collection("hot_knowledge")
        doc = {
            "content": content,
            "category": category,
            "test_count": 0,
            "success_count": 0,
            "created_at": datetime.now(),
            "last_tested": None,
            "confidence": 0.0
        }
        result = collection.insert_one(doc)
        return str(result.inserted_id)

    def update_knowledge_test(self, knowledge_id: str, success: bool):
        collection = self.get_collection("hot_knowledge")
        from bson import ObjectId
        update = {
            "$inc": {
                "test_count": 1,
                "success_count": 1 if success else 0
            },
            "$set": {"last_tested": datetime.now()}
        }
        collection.update_one({"_id": ObjectId(knowledge_id)}, update)

        # 更新置信度
        doc = collection.find_one({"_id": ObjectId(knowledge_id)})
        if doc and doc["test_count"] > 0:
            confidence = doc["success_count"] / doc["test_count"]
            collection.update_one(
                {"_id": ObjectId(knowledge_id)},
                {"$set": {"confidence": confidence}}
            )

    def get_top_hot_knowledge(self, limit: int = 10) -> List[Dict]:
        collection = self.get_collection("hot_knowledge")
        return list(collection.find().sort("confidence", -1).limit(limit))

    # 冷知识库操作
    def save_cold_knowledge(self, agent_name: str, content: str, from_hot: bool = True):
        collection = self.get_collection(f"cold_knowledge_{agent_name}")
        doc = {
            "agent_name": agent_name,
            "content": content,
            "promoted_from_hot": from_hot,
            "version": 1,
            "created_at": datetime.now()
        }
        collection.insert_one(doc)

    def get_agent_cold_knowledge(self, agent_name: str) -> List[Dict]:
        collection = self.get_collection(f"cold_knowledge_{agent_name}")
        return list(collection.find())

    # 复盘简报操作
    def save_review_brief(self, date: datetime, summary: str,
                         correct: List, wrong: List, insights: List):
        collection = self.get_collection("review_briefs")
        doc = {
            "date": date,
            "summary": summary,
            "correct_predictions": correct,
            "wrong_predictions": wrong,
            "key_insights": insights,
            "created_at": datetime.now()
        }
        collection.insert_one(doc)
