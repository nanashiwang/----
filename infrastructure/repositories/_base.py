from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import select


class SQLAlchemyRepository:
    def __init__(self, session_manager):
        self.session_manager = session_manager

    def _save(self, instance):
        with self.session_manager.session_scope() as session:
            session.add(instance)
        return instance

    def _bulk_save(self, instances: Iterable[Any]) -> list[Any]:
        instances = list(instances)
        with self.session_manager.session_scope() as session:
            session.add_all(instances)
        return instances

    def _one_or_none(self, model, *conditions):
        with self.session_manager.session_scope() as session:
            stmt = select(model)
            for condition in conditions:
                stmt = stmt.where(condition)
            return session.execute(stmt).scalar_one_or_none()

    def _all(self, model, *conditions, order_by=None) -> list[Any]:
        with self.session_manager.session_scope() as session:
            stmt = select(model)
            for condition in conditions:
                stmt = stmt.where(condition)
            if order_by is not None:
                stmt = stmt.order_by(order_by)
            return list(session.execute(stmt).scalars().all())
