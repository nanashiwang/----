import os
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from src.data.db.sqlite_client import SQLiteClient


class UserService:
    def __init__(self, db: SQLiteClient):
        self.db = db

    def create_user(self, username: str, password_hash: str, role: str = "user") -> int:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role)
            )
            conn.commit()
            return cursor.lastrowid

    def get_by_username(self, username: str) -> Optional[Dict]:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            return dict(row) if row else None

    def get_by_id(self, user_id: int) -> Optional[Dict]:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def list_all(self) -> List[Dict]:
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
            return [dict(r) for r in rows]

    def update_user(self, user_id: int, data: Dict):
        if not data:
            raise ValueError("至少提供一个可更新字段")
        with self.db.get_connection() as conn:
            sets = ", ".join(f"{k} = ?" for k in data)
            values = list(data.values()) + [user_id]
            conn.execute(f"UPDATE users SET {sets} WHERE id = ?", values)
            conn.commit()

    def update_last_login(self, user_id: int):
        with self.db.get_connection() as conn:
            conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.now(), user_id))
            conn.commit()

    def delete_user(self, user_id: int):
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()

    def ensure_admin_exists(self):
        """首次启动时根据环境变量显式初始化管理员账号"""
        with self.db.get_connection() as conn:
            admin_exists = conn.execute(
                "SELECT 1 FROM users WHERE role = 'admin' LIMIT 1"
            ).fetchone()
        if admin_exists:
            return

        username = os.getenv("INIT_ADMIN_USERNAME", "").strip()
        password = os.getenv("INIT_ADMIN_PASSWORD", "").strip()

        if not username or not password:
            logger.warning("未检测到管理员账号，且未配置 INIT_ADMIN_USERNAME / INIT_ADMIN_PASSWORD。系统不会自动创建默认管理员。")
            return

        existing_user = self.get_by_username(username)
        if existing_user:
            logger.warning("初始化管理员失败：用户 {} 已存在，请手动检查其权限。", username)
            return

        from backend.auth.jwt_handler import hash_password

        self.create_user(username, hash_password(password), "admin")
        logger.info("已根据环境变量初始化管理员账号：{}", username)
