import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.db.sqlite_client import SQLiteClient


class TestSQLiteClient(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.client = SQLiteClient(self.temp_db.name)

    def tearDown(self):
        os.unlink(self.temp_db.name)

    def test_legacy_tables_created_without_run_centric_tables(self):
        tables = set(self.client.list_tables())

        self.assertIn("event_briefs", tables)
        self.assertIn("stock_data", tables)
        self.assertIn("reviews", tables)
        self.assertIn("users", tables)
        self.assertIn("news_sources", tables)
        self.assertIn("market_data_snapshots", tables)
        self.assertIn(SQLiteClient.LEGACY_NEWS_ARTICLES_TABLE, tables)
        self.assertIn(SQLiteClient.LEGACY_RECOMMENDATIONS_TABLE, tables)
        self.assertIn(SQLiteClient.LEGACY_TRADES_TABLE, tables)

        for table_name in SQLiteClient.RUN_CENTRIC_TABLES:
            self.assertNotIn(table_name, tables)

        with self.client.get_connection() as conn:
            source_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(news_sources)").fetchall()
            }
        self.assertIn("priority", source_columns)
        self.assertIn("credibility", source_columns)

    def test_legacy_tables_still_support_write_paths(self):
        with self.client.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reviews (date, ts_code, analysis, lessons)
                VALUES (?, ?, ?, ?)
                """,
                ("2024-03-19", "600519.SH", "legacy analysis", "legacy lesson"),
            )
            conn.commit()

            row = conn.execute(
                "SELECT * FROM reviews WHERE ts_code = ?",
                ("600519.SH",),
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row["ts_code"], "600519.SH")
        self.assertEqual(row["analysis"], "legacy analysis")


if __name__ == "__main__":
    unittest.main()
