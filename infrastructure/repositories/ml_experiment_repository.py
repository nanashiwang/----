from __future__ import annotations

from sqlalchemy import select

from infrastructure.db.postgres.models import MLExperimentORM
from infrastructure.repositories._base import SQLAlchemyRepository


class MLExperimentRepository(SQLAlchemyRepository):
    def create(self, **kwargs):
        return self._save(MLExperimentORM(**kwargs))

    def list_by_group(self, experiment_group_id: str):
        with self.session_manager.session_scope() as session:
            stmt = (
                select(MLExperimentORM)
                .where(MLExperimentORM.experiment_group_id == experiment_group_id)
                .order_by(MLExperimentORM.experiment_mode.asc(), MLExperimentORM.created_at.asc())
            )
            return list(session.execute(stmt).scalars().all())

    def get(self, experiment_id: str):
        return self._one_or_none(MLExperimentORM, MLExperimentORM.experiment_id == experiment_id)
