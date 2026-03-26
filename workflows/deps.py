from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(slots=True)
class WorkflowDependencies:
    workflow_runs: WorkflowRunRepository
    agent_node_runs: AgentNodeRunRepository
    news_repository: NewsRepository
    daily_brief_repository: DailyBriefRepository
    feature_snapshot_repository: FeatureSnapshotRepository
    prediction_artifact_repository: PredictionArtifactRepository
    recommendation_repository: RecommendationRepository
    trade_repository: TradeRepository
    review_repository: ReviewRepository
    knowledge_repository: KnowledgeRepository
    market_data_client: object
    ocr_service: object
    llm_provider: object
    vectorstore_client: object
    settings: object | None = None
