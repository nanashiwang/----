import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager


class SQLiteClient:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _init_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 事件简报表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_briefs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    content TEXT NOT NULL,
                    source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 股票数据表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code VARCHAR(10) NOT NULL,
                    trade_date DATE NOT NULL,
                    open REAL, close REAL, high REAL, low REAL,
                    volume REAL, amount REAL,
                    UNIQUE(ts_code, trade_date)
                )
            """)

            # 推荐结果表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    ts_code VARCHAR(10) NOT NULL,
                    weight REAL,
                    reason TEXT,
                    agents_vote TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 交易记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code VARCHAR(10) NOT NULL,
                    trade_date DATE NOT NULL,
                    action VARCHAR(10),
                    price REAL,
                    volume INTEGER,
                    profit_loss REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 复盘记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    ts_code VARCHAR(10),
                    analysis TEXT,
                    lessons TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
