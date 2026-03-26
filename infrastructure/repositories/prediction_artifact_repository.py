from __future__ import annotations

from sqlalchemy import select

from core.ids import generate_prefixed_id
from infrastructure.db.postgres.models import PredictionArtifactORM
from infrastructure.repositories._base import SQLAlchemyRepository


class PredictionArtifactRepository(SQLAlchemyRepository):
    def bulk_create(self, rows: list[dict]):
        instances = [PredictionArtifactORM(artifact_id=generate_prefixed_id('artifact'), **row) for row in rows]
        return self._bulk_save(instances)

    def list_by_run(self, run_id: str):
        with self.session_manager.session_scope() as session:
            stmt = select(PredictionArtifactORM).where(PredictionArtifactORM.run_id == run_id)
            return list(session.execute(stmt).scalars().all())
