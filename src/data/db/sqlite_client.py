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

            # 用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(128) NOT NULL,
                    role VARCHAR(20) DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)

            # 系统配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category VARCHAR(50) NOT NULL,
                    key VARCHAR(100) NOT NULL,
                    value TEXT,
                    is_secret BOOLEAN DEFAULT 0,
                    updated_by INTEGER REFERENCES users(id),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, key)
                )
            """)

            # Agent配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cluster VARCHAR(20) NOT NULL,
                    agent_name VARCHAR(50) NOT NULL,
                    display_name VARCHAR(100),
                    system_prompt TEXT,
                    llm_provider VARCHAR(20),
                    llm_model VARCHAR(50),
                    is_enabled BOOLEAN DEFAULT 1,
                    parameters TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 资讯源配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    type VARCHAR(20) NOT NULL,
                    config TEXT NOT NULL,
                    is_enabled BOOLEAN DEFAULT 1,
                    fetch_interval INTEGER DEFAULT 3600,
                    last_fetched TIMESTAMP,
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
