from __future__ import annotations

from sqlalchemy import select

from core.ids import generate_prefixed_id
from infrastructure.db.postgres.models import TradeORM
from infrastructure.repositories._base import SQLAlchemyRepository


class TradeRepository(SQLAlchemyRepository):
    def create(self, **kwargs):
        return self._save(TradeORM(trade_id=generate_prefixed_id('trade'), **kwargs))

    def list_by_recommendation_run(self, recommendation_run_id: str):
        with self.session_manager.session_scope() as session:
            stmt = select(TradeORM).where(TradeORM.recommendation_run_id == recommendation_run_id)
            return list(session.execute(stmt).scalars().all())
