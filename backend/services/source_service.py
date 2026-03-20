from typing import List, Dict, Optional
from datetime import datetime
from src.data.db.sqlite_client import SQLiteClient


class SourceService:
    def __init__(self, db: SQLiteClient):
        self.db = db

    def list_all(self) -> List[Dict]:
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM news_sources ORDER BY id").fetchall()
            return [dict(r) for r in rows]

    def get_by_id(self, source_id: int) -> Optional[Dict]:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM news_sources WHERE id = ?", (source_id,)).fetchone()
            return dict(row) if row else None

    def create(self, data: Dict) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO news_sources (name, type, config, is_enabled, fetch_interval)
                VALUES (?, ?, ?, ?, ?)
            """, (data["name"], data["type"], data["config"],
                  data.get("is_enabled", True), data.get("fetch_interval", 3600)))
            conn.commit()
            return cursor.lastrowid

    def update(self, source_id: int, data: Dict):
        with self.db.get_connection() as conn:
            sets = ", ".join(f"{k} = ?" for k in data)
            values = list(data.values()) + [source_id]
            conn.execute(f"UPDATE news_sources SET {sets} WHERE id = ?", values)
            conn.commit()

    def delete(self, source_id: int):
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM news_sources WHERE id = ?", (source_id,))
            conn.commit()

    def update_last_fetched(self, source_id: int):
        with self.db.get_connection() as conn:
            conn.execute("UPDATE news_sources SET last_fetched = ? WHERE id = ?",
                         (datetime.now(), source_id))
            conn.commit()
