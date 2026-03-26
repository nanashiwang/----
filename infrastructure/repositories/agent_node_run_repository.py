from __future__ import annotations

from sqlalchemy import select

from infrastructure.db.postgres.models import AgentNodeRunORM
from infrastructure.repositories._base import SQLAlchemyRepository


class AgentNodeRunRepository(SQLAlchemyRepository):
    def start(self, **kwargs):
        return self._save(AgentNodeRunORM(**kwargs))

    def finish(self, node_run_id: str, **kwargs):
        with self.session_manager.session_scope() as session:
            instance = session.get(AgentNodeRunORM, node_run_id)
            if instance is None:
                return None
            for key, value in kwargs.items():
                setattr(instance, key, value)
            session.add(instance)
            return instance

    def fail(self, node_run_id: str, error_json: dict, **kwargs):
        payload = {'error_json': error_json, 'status': 'failed'}
        payload.update(kwargs)
        return self.finish(node_run_id, **payload)

    def list_by_run(self, run_id: str):
        with self.session_manager.session_scope() as session:
            stmt = select(AgentNodeRunORM).where(AgentNodeRunORM.run_id == run_id).order_by(AgentNodeRunORM.created_at.asc())
            return list(session.execute(stmt).scalars().all())
