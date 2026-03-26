import sqlite3
from contextlib import contextmanager
from pathlib import Path


class SQLiteClient:
    LEGACY_NEWS_ARTICLES_TABLE = "legacy_news_articles"
    LEGACY_RECOMMENDATIONS_TABLE = "legacy_recommendations"
    LEGACY_TRADES_TABLE = "legacy_trades"

    # Run-centric tables are managed only by Alembic migrations.
    # Do not add them back into this legacy initializer.
    RUN_CENTRIC_TABLES = {
        "workflow_runs",
        "agent_node_runs",
        "news_articles",
        "daily_briefs",
        "feature_snapshots",
        "prediction_artifacts",
        "recommendations",
        "trades",
        "review_reports",
    }

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _init_tables(self):
        with self.get_connection() as conn:
            # Legacy SQLite schema only. Run-centric tables must be created by Alembic.
            conn.execute("""
                CREATE TABLE IF NOT EXISTS event_briefs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    content TEXT NOT NULL,
                    source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code VARCHAR(10) NOT NULL,
                    trade_date DATE NOT NULL,
                    open REAL,
                    close REAL,
                    high REAL,
                    low REAL,
                    volume REAL,
                    amount REAL,
                    UNIQUE(ts_code, trade_date)
                )
            """)

            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.LEGACY_RECOMMENDATIONS_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    ts_code VARCHAR(10) NOT NULL,
                    weight REAL,
                    reason TEXT,
                    agents_vote TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.LEGACY_TRADES_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code VARCHAR(10) NOT NULL,
                    trade_date DATE NOT NULL,
                    action VARCHAR(10),
                    price REAL,
                    volume INTEGER,
                    profit_loss REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    ts_code VARCHAR(10),
                    analysis TEXT,
                    lessons TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
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

            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username VARCHAR(50) NOT NULL,
                    user_role VARCHAR(20) DEFAULT 'user',
                    module VARCHAR(30) NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    method VARCHAR(100) NOT NULL,
                    status VARCHAR(20) DEFAULT 'success',
                    label_column VARCHAR(80),
                    symbols_count INTEGER DEFAULT 0,
                    date_range_start DATE,
                    date_range_end DATE,
                    primary_metric_name VARCHAR(50),
                    primary_metric_value REAL,
                    secondary_metric_name VARCHAR(50),
                    secondary_metric_value REAL,
                    error_message TEXT,
                    parameters_json TEXT,
                    result_summary_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
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

            conn.execute("""
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

            conn.execute("""
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

            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.LEGACY_NEWS_ARTICLES_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER REFERENCES news_sources(id),
                    title TEXT NOT NULL,
                    summary TEXT,
                    content TEXT,
                    url TEXT,
                    published_at TIMESTAMP,
                    content_hash VARCHAR(64) NOT NULL,
                    symbols TEXT,
                    tags TEXT,
                    importance REAL DEFAULT 0.5,
                    raw_payload TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code VARCHAR(20) NOT NULL,
                    trade_date DATE NOT NULL,
                    dataset VARCHAR(30) NOT NULL,
                    metrics_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ts_code, trade_date, dataset)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_index_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    index_code VARCHAR(20) NOT NULL,
                    trade_date DATE NOT NULL,
                    open REAL,
                    close REAL,
                    high REAL,
                    low REAL,
                    pre_close REAL,
                    change REAL,
                    pct_chg REAL,
                    volume REAL,
                    amount REAL,
                    UNIQUE(index_code, trade_date)
                )
            """)

            self._ensure_column(conn, "news_sources", "category", "VARCHAR(50) DEFAULT ''")
            self._ensure_column(conn, "news_sources", "market", "VARCHAR(50) DEFAULT ''")
            self._ensure_column(conn, "news_sources", "dedup_strategy", "VARCHAR(50) DEFAULT 'content_hash'")
            self._ensure_column(conn, "news_sources", "parser", "VARCHAR(50) DEFAULT ''")
            self._ensure_column(conn, "news_sources", "priority", "REAL DEFAULT 0.5")
            self._ensure_column(conn, "news_sources", "credibility", "REAL DEFAULT 0.5")

            conn.execute(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_{self.LEGACY_NEWS_ARTICLES_TABLE}_unique_hash
                ON {self.LEGACY_NEWS_ARTICLES_TABLE}(content_hash)
                """
            )
            conn.execute(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_{self.LEGACY_NEWS_ARTICLES_TABLE}_unique_url
                ON {self.LEGACY_NEWS_ARTICLES_TABLE}(url) WHERE url IS NOT NULL AND url != ''
                """
            )
            conn.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_{self.LEGACY_NEWS_ARTICLES_TABLE}_published_at
                ON {self.LEGACY_NEWS_ARTICLES_TABLE}(published_at DESC)
                """
            )
            conn.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_{self.LEGACY_NEWS_ARTICLES_TABLE}_source_published
                ON {self.LEGACY_NEWS_ARTICLES_TABLE}(source_id, published_at DESC)
                """
            )
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_briefs_date_source
                ON event_briefs(date DESC, source)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stock_data_symbol_trade_date
                ON stock_data(ts_code, trade_date DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_data_snapshots_symbol_dataset_date
                ON market_data_snapshots(ts_code, dataset, trade_date DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_index_data_code_trade_date
                ON market_index_data(index_code, trade_date DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_logs_user_created_at
                ON usage_logs(user_id, created_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_logs_module_created_at
                ON usage_logs(module, created_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_logs_method_created_at
                ON usage_logs(method, created_at DESC)
            """)

            conn.commit()

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, definition: str):
        columns = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def list_tables(self) -> list[str]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return sorted(row[0] for row in rows)

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
