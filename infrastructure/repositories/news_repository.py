from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from core.ids import generate_prefixed_id
from infrastructure.db.postgres.models import NewsArticleORM
from infrastructure.repositories._base import SQLAlchemyRepository


class NewsRepository(SQLAlchemyRepository):
    def upsert_article(self, article: dict):
        content_hash = article.get('content_hash') or self._build_hash(article)
        with self.session_manager.session_scope() as session:
            stmt = select(NewsArticleORM).where(NewsArticleORM.content_hash == content_hash)
            instance = session.execute(stmt).scalar_one_or_none()
            if instance is None:
                instance = NewsArticleORM(
                    article_id=generate_prefixed_id('article'),
                    content_hash=content_hash,
                    source=article.get('source', 'unknown'),
                    title=article.get('title', ''),
                    url=article.get('url', ''),
                    published_at=article.get('published_at'),
                    summary=article.get('summary', ''),
                    content=article.get('content', ''),
                    symbols_json={'symbols': article.get('symbols', [])},
                    metadata_json=article.get('metadata', {}),
                    ingested_run_id=article.get('ingested_run_id'),
                )
            else:
                instance.title = article.get('title', instance.title)
                instance.url = article.get('url', instance.url)
                instance.summary = article.get('summary', instance.summary)
                instance.content = article.get('content', instance.content)
                instance.metadata_json = article.get('metadata', instance.metadata_json)
            session.add(instance)
            return instance

    def list_recent(self, as_of_date: date, hours: int = 24):
        end_dt = datetime.combine(as_of_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        start_dt = end_dt - timedelta(hours=hours)
        with self.session_manager.session_scope() as session:
            stmt = (
                select(NewsArticleORM)
                .where(NewsArticleORM.published_at >= start_dt)
                .where(NewsArticleORM.published_at <= end_dt)
                .order_by(NewsArticleORM.published_at.desc())
            )
            return list(session.execute(stmt).scalars().all())

    def count(self) -> int:
        with self.session_manager.session_scope() as session:
            return len(list(session.execute(select(NewsArticleORM.article_id)).all()))

    @staticmethod
    def _build_hash(article: dict) -> str:
        raw = '|'.join([
            article.get('source', ''),
            article.get('title', ''),
            article.get('url', ''),
            article.get('content', ''),
        ])
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()
