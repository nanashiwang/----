from __future__ import annotations

from sqlalchemy import select

from infrastructure.db.postgres.models import WorkflowRunORM
from infrastructure.repositories._base import SQLAlchemyRepository


class WorkflowRunRepository(SQLAlchemyRepository):
    def get(self, run_id: str):
        return self._one_or_none(WorkflowRunORM, WorkflowRunORM.run_id == run_id)

    def get_by_idempotency_key(self, idempotency_key: str):
        if not idempotency_key:
            return None
        return self._one_or_none(WorkflowRunORM, WorkflowRunORM.idempotency_key == idempotency_key)

    def create(self, **kwargs):
        return self._save(WorkflowRunORM(**kwargs))

    def update(self, run_id: str, **kwargs):
        with self.session_manager.session_scope() as session:
            instance = session.get(WorkflowRunORM, run_id)
            if instance is None:
                return None
            for key, value in kwargs.items():
                setattr(instance, key, value)
            session.add(instance)
            return instance

    def list_recent(self, limit: int = 50):
        with self.session_manager.session_scope() as session:
            stmt = select(WorkflowRunORM).order_by(WorkflowRunORM.created_at.desc()).limit(limit)
            return list(session.execute(stmt).scalars().all())
