from __future__ import annotations

from functools import lru_cache

from core.config import Settings, get_settings
from infrastructure.db.postgres.session import SessionManager
from infrastructure.llm.provider import LLMProvider
from infrastructure.market_data.tushare_client import TushareMarketDataClient
from infrastructure.ocr.trade_ocr import TradeOCRService
from infrastructure.repositories import (
    AgentNodeRunRepository,
    DailyBriefRepository,
    FeatureSnapshotRepository,
    KnowledgeAnalyticsRepository,
    KnowledgeRepository,
    MLExperimentRepository,
    NewsRepository,
    PredictionArtifactRepository,
    RecommendationRepository,
    ReviewRepository,
    TradeRepository,
    WorkflowRunRepository,
)
from memory.analytics import KnowledgeAnalyticsService
from infrastructure.vectorstore.client import VectorStoreClient
from ml.service import MLExperimentService
from workflows.deps import WorkflowDependencies
from workflows.service import WorkflowApplicationService


@lru_cache(maxsize=1)
def get_app_settings() -> Settings:
    return get_settings()


@lru_cache(maxsize=1)
def get_session_manager() -> SessionManager:
    return SessionManager(get_app_settings().postgres_dsn)


def build_workflow_dependencies() -> WorkflowDependencies:
    settings = get_app_settings()
    session_manager = get_session_manager()
    return WorkflowDependencies(
        workflow_runs=WorkflowRunRepository(session_manager),
        agent_node_runs=AgentNodeRunRepository(session_manager),
        news_repository=NewsRepository(session_manager),
        daily_brief_repository=DailyBriefRepository(session_manager),
        feature_snapshot_repository=FeatureSnapshotRepository(session_manager),
        prediction_artifact_repository=PredictionArtifactRepository(session_manager),
        recommendation_repository=RecommendationRepository(session_manager),
        trade_repository=TradeRepository(session_manager),
        review_repository=ReviewRepository(session_manager),
        knowledge_repository=KnowledgeRepository(session_manager),
        market_data_client=TushareMarketDataClient(
            token=settings.tushare_token,
            api_url=settings.tushare_api_url,
            default_watchlist=[item.strip().upper() for item in settings.default_watchlist.split(',') if item.strip()],
        ),
        ocr_service=TradeOCRService(),
        llm_provider=LLMProvider(),
        vectorstore_client=VectorStoreClient(settings.vectorstore_uri),
        settings=settings,
    )


@lru_cache(maxsize=1)
def get_workflow_service() -> WorkflowApplicationService:
    from apps.worker.tasks.workflow_tasks import dispatch_workflow_run

    return WorkflowApplicationService(build_workflow_dependencies, async_dispatcher=dispatch_workflow_run)


@lru_cache(maxsize=1)
def get_ml_service() -> MLExperimentService:
    settings = get_app_settings()
    return MLExperimentService(
        feature_snapshot_repository=FeatureSnapshotRepository(get_session_manager()),
        daily_brief_repository=DailyBriefRepository(get_session_manager()),
        ml_experiment_repository=MLExperimentRepository(get_session_manager()),
        tracking_uri=settings.mlflow_tracking_uri,
    )


def get_knowledge_repository() -> KnowledgeRepository:
    return KnowledgeRepository(get_session_manager())


@lru_cache(maxsize=1)
def get_knowledge_analytics_service() -> KnowledgeAnalyticsService:
    return KnowledgeAnalyticsService(
        analytics_repository=KnowledgeAnalyticsRepository(get_session_manager()),
        knowledge_repository=KnowledgeRepository(get_session_manager()),
    )
