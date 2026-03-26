from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, or_, select

from core.enums import KnowledgeStatus
from infrastructure.db.postgres.models import (
    ColdKnowledgeORM,
    HotKnowledgeORM,
    KnowledgeEventORM,
    RecommendationORM,
    ReviewReportORM,
)
from infrastructure.repositories._base import SQLAlchemyRepository


class KnowledgeAnalyticsRepository(SQLAlchemyRepository):
    def get_review_trend_windows(self, window_sizes: list[int]):
        normalized_sizes = sorted({int(size) for size in window_sizes if int(size) > 0})
        if not normalized_sizes:
            return {}

        max_window = max(normalized_sizes)
        with self.session_manager.session_scope() as session:
            stmt = (
                select(ReviewReportORM)
                .order_by(ReviewReportORM.as_of_date.desc(), ReviewReportORM.created_at.desc())
                .limit(max_window)
            )
            rows = list(session.execute(stmt).scalars().all())
        return {size: list(rows[:size]) for size in normalized_sizes}

    def list_hot_knowledge(self, include_archived: bool = True, limit: int = 500):
        with self.session_manager.session_scope() as session:
            stmt = select(HotKnowledgeORM).order_by(HotKnowledgeORM.updated_at.desc())
            if not include_archived:
                stmt = stmt.where(HotKnowledgeORM.status != KnowledgeStatus.ARCHIVED)
            if limit > 0:
                stmt = stmt.limit(limit)
            return list(session.execute(stmt).scalars().all())

    def list_cold_knowledge(
        self,
        include_archived: bool = True,
        include_degraded: bool = True,
        limit: int = 500,
    ):
        with self.session_manager.session_scope() as session:
            stmt = select(ColdKnowledgeORM).order_by(ColdKnowledgeORM.updated_at.desc())
            statuses = [KnowledgeStatus.ACTIVE]
            if include_degraded:
                statuses.append(KnowledgeStatus.DEGRADED)
            if include_archived:
                statuses.append(KnowledgeStatus.ARCHIVED)
            stmt = stmt.where(ColdKnowledgeORM.status.in_(statuses))
            if limit > 0:
                stmt = stmt.limit(limit)
            return list(session.execute(stmt).scalars().all())

    def list_review_reports(
        self,
        *,
        window_type: str = 'all_time',
        window_value: int | None = None,
        limit: int = 5000,
    ):
        with self.session_manager.session_scope() as session:
            stmt = select(ReviewReportORM).order_by(ReviewReportORM.as_of_date.desc(), ReviewReportORM.created_at.desc())
            if window_type == 'reviews' and window_value:
                stmt = stmt.limit(window_value)
                return list(session.execute(stmt).scalars().all())

            rows = list(session.execute(stmt.limit(limit) if limit > 0 else stmt).scalars().all())
            if window_type == 'days' and window_value:
                latest_date = session.execute(select(func.max(ReviewReportORM.as_of_date))).scalar_one_or_none()
                if latest_date is None:
                    return []
                cutoff = latest_date - timedelta(days=max(window_value - 1, 0))
                rows = [row for row in rows if row.as_of_date >= cutoff]
            return rows

    def list_recommendations(
        self,
        *,
        run_ids: list[str] | None = None,
        recommendation_ids: list[str] | None = None,
        limit: int = 5000,
    ):
        with self.session_manager.session_scope() as session:
            stmt = select(RecommendationORM).order_by(RecommendationORM.created_at.desc())
            if run_ids is not None:
                if not run_ids:
                    return []
                stmt = stmt.where(RecommendationORM.run_id.in_(run_ids))
            if recommendation_ids is not None:
                if not recommendation_ids:
                    return []
                stmt = stmt.where(RecommendationORM.recommendation_id.in_(recommendation_ids))
            if limit > 0:
                stmt = stmt.limit(limit)
            return list(session.execute(stmt).scalars().all())

    def list_knowledge_events(
        self,
        *,
        source_run_ids: list[str] | None = None,
        source_review_report_ids: list[str] | None = None,
        limit: int = 5000,
    ):
        with self.session_manager.session_scope() as session:
            stmt = select(KnowledgeEventORM).order_by(KnowledgeEventORM.created_at.desc())
            filters = []
            if source_run_ids is not None:
                if source_run_ids:
                    filters.append(KnowledgeEventORM.source_run_id.in_(source_run_ids))
                elif source_review_report_ids is None:
                    return []
            if source_review_report_ids is not None:
                if source_review_report_ids:
                    filters.append(KnowledgeEventORM.source_review_report_id.in_(source_review_report_ids))
                elif source_run_ids is None:
                    return []
            if filters:
                stmt = stmt.where(or_(*filters))
            if limit > 0:
                stmt = stmt.limit(limit)
            return list(session.execute(stmt).scalars().all())
