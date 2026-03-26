from __future__ import annotations

from sqlalchemy import select

from core.ids import generate_prefixed_id
from infrastructure.db.postgres.models import FeatureSnapshotORM
from infrastructure.repositories._base import SQLAlchemyRepository


class FeatureSnapshotRepository(SQLAlchemyRepository):
    def upsert_snapshot(self, **kwargs):
        with self.session_manager.session_scope() as session:
            stmt = (
                select(FeatureSnapshotORM)
                .where(FeatureSnapshotORM.run_id == kwargs['run_id'])
                .where(FeatureSnapshotORM.symbol == kwargs['symbol'])
                .where(FeatureSnapshotORM.snapshot_type == kwargs['snapshot_type'])
            )
            instance = session.execute(stmt).scalar_one_or_none()
            if instance is None:
                instance = FeatureSnapshotORM(snapshot_id=generate_prefixed_id('snapshot'), **kwargs)
            else:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
            session.add(instance)
            return instance

    def list_by_date(self, as_of_date, snapshot_type: str | None = None):
        with self.session_manager.session_scope() as session:
            stmt = select(FeatureSnapshotORM).where(FeatureSnapshotORM.as_of_date == as_of_date)
            if snapshot_type:
                stmt = stmt.where(FeatureSnapshotORM.snapshot_type == snapshot_type)
            stmt = stmt.order_by(FeatureSnapshotORM.symbol.asc())
            return list(session.execute(stmt).scalars().all())
