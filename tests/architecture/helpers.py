from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from core.config import Settings
from infrastructure.db.postgres.session import SessionManager
from infrastructure.llm.provider import LLMProvider
from infrastructure.market_data.tushare_client import TushareMarketDataClient
from infrastructure.ocr.trade_ocr import TradeOCRService
from infrastructure.repositories import (
    AgentNodeRunRepository,
    DailyBriefRepository,
    FeatureSnapshotRepository,
    KnowledgeRepository,
    NewsRepository,
    PredictionArtifactRepository,
    RecommendationRepository,
    ReviewRepository,
    TradeRepository,
    WorkflowRunRepository,
)
from infrastructure.vectorstore.client import VectorStoreClient
from workflows.deps import WorkflowDependencies


class FakeTradeOCRService(TradeOCRService):
    def parse(self, image_path: str):
        result = super().parse(image_path)
        result.symbol = '600519.SH'
        result.side = 'buy'
        result.price = 123.45
        result.quantity = 100
        result.trade_date = date(2026, 3, 25)
        result.confidence = 0.88
        return result


@dataclass(slots=True)
class TestHarness:
    session_manager: SessionManager
    deps: WorkflowDependencies


def build_test_harness() -> TestHarness:
    session_manager = SessionManager('sqlite+pysqlite:///:memory:')
    session_manager.init_schema()
    settings = Settings(
        POSTGRES_DSN='sqlite+pysqlite:///:memory:',
        DEFAULT_WATCHLIST='000001.SZ,600519.SH,300750.SZ',
    )
    deps = WorkflowDependencies(
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
        market_data_client=TushareMarketDataClient(default_watchlist=['000001.SZ', '600519.SH', '300750.SZ']),
        ocr_service=FakeTradeOCRService(),
        llm_provider=LLMProvider(),
        vectorstore_client=VectorStoreClient(),
        settings=settings,
    )
    return TestHarness(session_manager=session_manager, deps=deps)
