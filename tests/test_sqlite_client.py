import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.db.sqlite_client import SQLiteClient
import tempfile
import os


class TestSQLiteClient(unittest.TestCase):
    """测试SQLite客户端"""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.client = SQLiteClient(self.temp_db.name)

    def tearDown(self):
        os.unlink(self.temp_db.name)

    def test_tables_created(self):
        """测试表是否创建"""
        with self.client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            self.assertIn('event_briefs', tables)
            self.assertIn('stock_data', tables)
            self.assertIn('recommendations', tables)
            self.assertIn('trades', tables)
            self.assertIn('reviews', tables)

    def test_insert_recommendation(self):
        """测试插入推荐"""
        with self.client.get_connection() as conn:
            conn.execute("""
                INSERT INTO recommendations (date, ts_code, weight, reason)
                VALUES (?, ?, ?, ?)
            """, ('2024-03-19', '600519.SH', 0.8, '测试理由'))
            conn.commit()

            cursor = conn.cursor()
            cursor.execute("SELECT * FROM recommendations WHERE ts_code = ?", ('600519.SH',))
            row = cursor.fetchone()

            self.assertIsNotNone(row)
            self.assertEqual(row['ts_code'], '600519.SH')
            self.assertEqual(row['weight'], 0.8)


if __name__ == '__main__':
    unittest.main()
