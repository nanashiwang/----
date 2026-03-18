import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.knowledge.hot_kb import HotKnowledgeBase
from src.data.db.mongo_client import MongoDBClient
from unittest.mock import Mock, MagicMock


class TestHotKnowledgeBase(unittest.TestCase):
    """测试热知识库"""

    def setUp(self):
        self.mock_mongo = Mock(spec=MongoDBClient)
        self.hot_kb = HotKnowledgeBase(self.mock_mongo)

    def test_add_experience(self):
        """测试添加经验"""
        self.mock_mongo.add_hot_knowledge.return_value = "test_id"

        result = self.hot_kb.add_experience("测试经验", "技术面")

        self.mock_mongo.add_hot_knowledge.assert_called_once_with("测试经验", "技术面")
        self.assertEqual(result, "test_id")

    def test_test_experience(self):
        """测试经验测试"""
        self.hot_kb.test_experience("test_id", True)

        self.mock_mongo.update_knowledge_test.assert_called_once_with("test_id", True)


if __name__ == '__main__':
    unittest.main()
