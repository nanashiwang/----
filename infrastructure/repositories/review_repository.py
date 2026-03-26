from __future__ import annotations

from sqlalchemy import select

from core.ids import generate_prefixed_id
from infrastructure.db.postgres.models import ReviewReportORM
from infrastructure.repositories._base import SQLAlchemyRepository


class ReviewRepository(SQLAlchemyRepository):
    def create(self, **kwargs):
        review_report_id = kwargs.pop('review_report_id', generate_prefixed_id('review'))
        return self._save(ReviewReportORM(review_report_id=review_report_id, **kwargs))

    def list_by_target_run(self, target_run_id: str):
        with self.session_manager.session_scope() as session:
            stmt = select(ReviewReportORM).where(ReviewReportORM.target_run_id == target_run_id)
            return list(session.execute(stmt).scalars().all())

    def get_by_run(self, run_id: str):
        return self._one_or_none(ReviewReportORM, ReviewReportORM.run_id == run_id)
