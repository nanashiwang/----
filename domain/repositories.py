from __future__ import annotations

from datetime import date
from typing import Any, Protocol


class WorkflowRunRepositoryProtocol(Protocol):
    def get(self, run_id: str) -> Any: ...
    def get_by_idempotency_key(self, idempotency_key: str) -> Any: ...
    def create(self, **kwargs: Any) -> Any: ...
    def update(self, run_id: str, **kwargs: Any) -> Any: ...


class AgentNodeRunRepositoryProtocol(Protocol):
    def start(self, **kwargs: Any) -> Any: ...
    def finish(self, node_run_id: str, **kwargs: Any) -> Any: ...
    def fail(self, node_run_id: str, error_json: dict[str, Any]) -> Any: ...
    def list_by_run(self, run_id: str) -> list[Any]: ...


class NewsRepositoryProtocol(Protocol):
    def upsert_article(self, article: dict[str, Any]) -> Any: ...
    def list_recent(self, as_of_date: date, hours: int = 24) -> list[Any]: ...


class FeatureSnapshotRepositoryProtocol(Protocol):
    def upsert_snapshot(self, **kwargs: Any) -> Any: ...
    def list_by_date(self, as_of_date: date, snapshot_type: str | None = None) -> list[Any]: ...


class RecommendationRepositoryProtocol(Protocol):
    def bulk_create(self, rows: list[dict[str, Any]]) -> list[Any]: ...
    def list_by_run(self, run_id: str) -> list[Any]: ...


class TradeRepositoryProtocol(Protocol):
    def create(self, **kwargs: Any) -> Any: ...
    def list_by_recommendation_run(self, recommendation_run_id: str) -> list[Any]: ...


class ReviewRepositoryProtocol(Protocol):
    def create(self, **kwargs: Any) -> Any: ...
    def get_by_run(self, run_id: str) -> Any: ...
    def list_by_target_run(self, target_run_id: str) -> list[Any]: ...


class KnowledgeRepositoryProtocol(Protocol):
    def get_hot(self, knowledge_id: str) -> Any: ...
    def create_hot_knowledge(
        self,
        item: dict[str, Any],
        source_run_id: str | None = None,
        source_review_report_id: str | None = None,
        event_type: str = 'hot_created',
    ) -> Any: ...
    def update_hot_knowledge_stats(
        self,
        knowledge_id: str,
        item: dict[str, Any],
        source_run_id: str | None = None,
        source_review_report_id: str | None = None,
    ) -> Any: ...
    def upsert_hot(
        self,
        item: dict[str, Any],
        source_run_id: str | None = None,
        source_review_report_id: str | None = None,
    ) -> Any: ...
    def list_hot(self, limit: int = 100) -> list[Any]: ...
    def list_promotable_hot_knowledge(
        self,
        min_tests: int = 10,
        min_pass_rate: float = 0.65,
        min_market_regimes: int = 2,
        limit: int = 100,
    ) -> list[Any]: ...
    def get_active_cold_knowledge(
        self,
        category: str | None = None,
        market_regime: str | None = None,
        limit: int = 100,
    ) -> list[Any]: ...
    def promote_to_cold(
        self,
        knowledge_id: str,
        promotion_reason: str,
        promotion_run_id: str,
        source_review_report_id: str | None = None,
    ) -> Any: ...
    def record_cold_validation(
        self,
        cold_knowledge_id: str,
        passed: bool,
        source_run_id: str | None = None,
        source_review_report_id: str | None = None,
        details_json: dict[str, Any] | None = None,
    ) -> Any: ...
    def demote_cold_knowledge(
        self,
        knowledge_id: str,
        reason: str,
        source_run_id: str | None = None,
        source_review_report_id: str | None = None,
        archive: bool = False,
    ) -> Any: ...
    def append_knowledge_event(
        self,
        knowledge_id: str,
        knowledge_type: str,
        event_type: str,
        source_run_id: str | None = None,
        source_review_report_id: str | None = None,
        details_json: dict[str, Any] | None = None,
    ) -> Any: ...
    def archive(self, knowledge_id: str, reason: str) -> Any: ...
