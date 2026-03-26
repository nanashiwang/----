from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import FlowType, KnowledgeStatus, RecommendationAction, RunStatus, SnapshotType
from infrastructure.db.postgres.base import Base, TimestampMixin


class WorkflowRunORM(Base, TimestampMixin):
    __tablename__ = 'workflow_runs'

    run_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    flow_type: Mapped[FlowType] = mapped_column(SAEnum(FlowType, native_enum=False), nullable=False)
    status: Mapped[RunStatus] = mapped_column(SAEnum(RunStatus, native_enum=False), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    trigger_source: Mapped[str] = mapped_column(String(50), default='manual', nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(120), unique=True)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    agent_version: Mapped[str] = mapped_column(String(50), nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    input_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AgentNodeRunORM(Base, TimestampMixin):
    __tablename__ = 'agent_node_runs'

    node_run_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('workflow_runs.run_id'), nullable=False, index=True)
    flow_type: Mapped[FlowType] = mapped_column(SAEnum(FlowType, native_enum=False), nullable=False)
    node_name: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    input_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    evidence_refs_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class NewsArticleORM(Base, TimestampMixin):
    __tablename__ = 'news_articles'
    __table_args__ = (UniqueConstraint('content_hash', name='uq_news_articles_content_hash'),)

    article_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    ingested_run_id: Mapped[Optional[str]] = mapped_column(ForeignKey('workflow_runs.run_id'))
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), default='', nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    summary: Mapped[str] = mapped_column(Text, default='', nullable=False)
    content: Mapped[str] = mapped_column(Text, default='', nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    symbols_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class DailyBriefORM(Base, TimestampMixin):
    __tablename__ = 'daily_briefs'

    brief_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('workflow_runs.run_id'), nullable=False, index=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    brief_type: Mapped[str] = mapped_column(String(50), default='daily_brief', nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class FeatureSnapshotORM(Base, TimestampMixin):
    __tablename__ = 'feature_snapshots'
    __table_args__ = (
        UniqueConstraint('run_id', 'symbol', 'snapshot_type', name='uq_feature_snapshots_run_symbol_type'),
    )

    snapshot_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('workflow_runs.run_id'), nullable=False, index=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    snapshot_type: Mapped[SnapshotType] = mapped_column(SAEnum(SnapshotType, native_enum=False), nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String(50), nullable=False)
    features_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class PredictionArtifactORM(Base, TimestampMixin):
    __tablename__ = 'prediction_artifacts'

    artifact_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('workflow_runs.run_id'), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String(50), nullable=False)
    ml_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    event_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    technical_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    debate_consensus_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    risk_adjusted_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    artifact_uri: Mapped[str] = mapped_column(String(1024), default='', nullable=False)
    explanation_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class RecommendationORM(Base, TimestampMixin):
    __tablename__ = 'recommendations'

    recommendation_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('workflow_runs.run_id'), nullable=False, index=True)
    prediction_artifact_id: Mapped[Optional[str]] = mapped_column(ForeignKey('prediction_artifacts.artifact_id'))
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    action: Mapped[RecommendationAction] = mapped_column(
        SAEnum(RecommendationAction, native_enum=False),
        nullable=False,
    )
    weight: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default='', nullable=False)
    risk_flags_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class TradeORM(Base, TimestampMixin):
    __tablename__ = 'trades'

    trade_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('workflow_runs.run_id'), nullable=False, index=True)
    recommendation_id: Mapped[Optional[str]] = mapped_column(ForeignKey('recommendations.recommendation_id'))
    recommendation_run_id: Mapped[Optional[str]] = mapped_column(ForeignKey('workflow_runs.run_id'))
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    fees: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    screenshot_uri: Mapped[str] = mapped_column(String(1024), default='', nullable=False)
    ocr_raw_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    confirmation_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ReviewReportORM(Base, TimestampMixin):
    __tablename__ = 'review_reports'

    review_report_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('workflow_runs.run_id'), nullable=False, index=True)
    target_run_id: Mapped[str] = mapped_column(ForeignKey('workflow_runs.run_id'), nullable=False, index=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    horizon: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    verdicts_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    knowledge_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class HotKnowledgeORM(Base, TimestampMixin):
    __tablename__ = 'hot_knowledge'

    knowledge_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    lineage_id: Mapped[Optional[str]] = mapped_column(String(40), index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_run_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    source_recommendation_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    tests_survived: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pass_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fail_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pass_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    applicable_event_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    applicable_technical_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    applicable_market_regimes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    negative_match_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[KnowledgeStatus] = mapped_column(
        SAEnum(KnowledgeStatus, native_enum=False),
        default=KnowledgeStatus.ACTIVE,
        nullable=False,
    )
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ColdKnowledgeORM(Base, TimestampMixin):
    __tablename__ = 'cold_knowledge'

    knowledge_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    lineage_id: Mapped[Optional[str]] = mapped_column(String(40), index=True)
    source_hot_knowledge_id: Mapped[str] = mapped_column(ForeignKey('hot_knowledge.knowledge_id'), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    promotion_reason: Mapped[str] = mapped_column(Text, default='', nullable=False)
    promotion_run_id: Mapped[str] = mapped_column(ForeignKey('workflow_runs.run_id'), nullable=False, index=True)
    source_run_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    source_recommendation_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    tests_survived: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pass_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fail_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pass_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    applicable_event_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    applicable_technical_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    applicable_market_regimes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    negative_match_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    invalid_conditions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[KnowledgeStatus] = mapped_column(
        SAEnum(KnowledgeStatus, native_enum=False),
        default=KnowledgeStatus.ACTIVE,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class KnowledgeEventORM(Base, TimestampMixin):
    __tablename__ = 'knowledge_events'

    event_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    knowledge_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    knowledge_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_run_id: Mapped[Optional[str]] = mapped_column(ForeignKey('workflow_runs.run_id'))
    source_review_report_id: Mapped[Optional[str]] = mapped_column(ForeignKey('review_reports.review_report_id'))
    details_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class MLExperimentORM(Base, TimestampMixin):
    __tablename__ = 'ml_experiments'

    experiment_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    experiment_group_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    experiment_mode: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    dataset_version: Mapped[str] = mapped_column(String(50), nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String(50), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    tag_encoder_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    label_horizon: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    cv_method: Mapped[str] = mapped_column(String(50), nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(1024), default='', nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    params_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    shap_summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
