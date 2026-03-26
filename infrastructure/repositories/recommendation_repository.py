from __future__ import annotations

from sqlalchemy import select

from core.ids import generate_prefixed_id
from infrastructure.db.postgres.models import RecommendationORM
from infrastructure.repositories._base import SQLAlchemyRepository


class RecommendationRepository(SQLAlchemyRepository):
    def bulk_create(self, rows: list[dict]):
        instances = [RecommendationORM(recommendation_id=generate_prefixed_id('rec'), **row) for row in rows]
        return self._bulk_save(instances)

    def list_by_run(self, run_id: str):
        with self.session_manager.session_scope() as session:
            stmt = select(RecommendationORM).where(RecommendationORM.run_id == run_id).order_by(RecommendationORM.final_score.desc())
            return list(session.execute(stmt).scalars().all())
