from __future__ import annotations

from sqlalchemy import select

from core.ids import generate_prefixed_id
from infrastructure.db.postgres.models import DailyBriefORM
from infrastructure.repositories._base import SQLAlchemyRepository


class DailyBriefRepository(SQLAlchemyRepository):
    def upsert_brief(self, **kwargs):
        with self.session_manager.session_scope() as session:
            stmt = (
                select(DailyBriefORM)
                .where(DailyBriefORM.as_of_date == kwargs['as_of_date'])
                .where(DailyBriefORM.brief_type == kwargs.get('brief_type', 'daily_brief'))
            )
            instance = session.execute(stmt).scalar_one_or_none()
            if instance is None:
                instance = DailyBriefORM(brief_id=generate_prefixed_id('brief'), **kwargs)
            else:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
            session.add(instance)
            return instance

    def latest_for_date(self, as_of_date):
        return self._one_or_none(DailyBriefORM, DailyBriefORM.as_of_date == as_of_date)

    def list_history(self, as_of_date, limit: int = 30):
        with self.session_manager.session_scope() as session:
            stmt = (
                select(DailyBriefORM)
                .where(DailyBriefORM.as_of_date < as_of_date)
                .order_by(DailyBriefORM.as_of_date.desc())
                .limit(limit)
            )
            return list(session.execute(stmt).scalars().all())
