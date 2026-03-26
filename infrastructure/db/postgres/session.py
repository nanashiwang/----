from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.engine import make_url

from infrastructure.db.postgres.base import Base


class SessionManager:
    def __init__(self, dsn: str):
        self._ensure_sqlite_directory(dsn)
        engine_kwargs = {"future": True, "pool_pre_ping": True}
        if dsn.startswith("sqlite") and ":memory:" in dsn:
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            engine_kwargs["poolclass"] = StaticPool
        self.engine = create_engine(dsn, **engine_kwargs)
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False, class_=Session)

    @staticmethod
    def _ensure_sqlite_directory(dsn: str) -> None:
        url = make_url(dsn)
        if not url.drivername.startswith("sqlite"):
            return
        if not url.database or url.database == ":memory:":
            return
        db_path = Path(url.database)
        if not db_path.is_absolute():
            db_path = Path.cwd() / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def session_scope(self):
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def init_schema(self) -> None:
        # Dev/test convenience only. Production schema changes should go through Alembic.
        Base.metadata.create_all(self.engine)
