"""create run centric tables

Revision ID: 20260326_0001
Revises:
Create Date: 2026-03-26 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260326_0001"
down_revision = None
branch_labels = None
depends_on = None


flow_type_enum = sa.Enum("observe", "reason", "act", "review", name="flowtype", native_enum=False)
run_status_enum = sa.Enum(
    "pending",
    "running",
    "waiting_for_user",
    "completed",
    "failed",
    name="runstatus",
    native_enum=False,
)
snapshot_type_enum = sa.Enum("market", "indicator", name="snapshottype", native_enum=False)
recommendation_action_enum = sa.Enum("include", "watch", "exclude", name="recommendationaction", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("run_id", sa.String(length=40), primary_key=True),
        sa.Column("flow_type", flow_type_enum, nullable=False),
        sa.Column("status", run_status_enum, nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("trigger_source", sa.String(length=50), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("agent_version", sa.String(length=50), nullable=False),
        sa.Column("feature_set_version", sa.String(length=50), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("error_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_workflow_runs_idempotency_key"),
    )
    op.create_index("ix_workflow_runs_as_of_date", "workflow_runs", ["as_of_date"])
    op.create_index("ix_workflow_runs_flow_type", "workflow_runs", ["flow_type"])

    op.create_table(
        "agent_node_runs",
        sa.Column("node_run_id", sa.String(length=40), primary_key=True),
        sa.Column("run_id", sa.String(length=40), sa.ForeignKey("workflow_runs.run_id"), nullable=False),
        sa.Column("flow_type", flow_type_enum, nullable=False),
        sa.Column("node_name", sa.String(length=100), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("evidence_refs_json", sa.JSON(), nullable=False),
        sa.Column("error_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_node_runs_run_id", "agent_node_runs", ["run_id"])

    op.create_table(
        "news_articles",
        sa.Column("article_id", sa.String(length=40), primary_key=True),
        sa.Column("ingested_run_id", sa.String(length=40), sa.ForeignKey("workflow_runs.run_id"), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("symbols_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("content_hash", name="uq_news_articles_content_hash"),
    )
    op.create_index("ix_news_articles_published_at", "news_articles", ["published_at"])

    op.create_table(
        "daily_briefs",
        sa.Column("brief_id", sa.String(length=40), primary_key=True),
        sa.Column("run_id", sa.String(length=40), sa.ForeignKey("workflow_runs.run_id"), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("brief_type", sa.String(length=50), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_daily_briefs_run_id", "daily_briefs", ["run_id"])
    op.create_index("ix_daily_briefs_as_of_date", "daily_briefs", ["as_of_date"])

    op.create_table(
        "feature_snapshots",
        sa.Column("snapshot_id", sa.String(length=40), primary_key=True),
        sa.Column("run_id", sa.String(length=40), sa.ForeignKey("workflow_runs.run_id"), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("snapshot_type", snapshot_type_enum, nullable=False),
        sa.Column("feature_set_version", sa.String(length=50), nullable=False),
        sa.Column("features_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "symbol", "snapshot_type", name="uq_feature_snapshots_run_symbol_type"),
    )
    op.create_index("ix_feature_snapshots_run_id", "feature_snapshots", ["run_id"])
    op.create_index("ix_feature_snapshots_as_of_date", "feature_snapshots", ["as_of_date"])
    op.create_index("ix_feature_snapshots_symbol", "feature_snapshots", ["symbol"])

    op.create_table(
        "prediction_artifacts",
        sa.Column("artifact_id", sa.String(length=40), primary_key=True),
        sa.Column("run_id", sa.String(length=40), sa.ForeignKey("workflow_runs.run_id"), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("feature_set_version", sa.String(length=50), nullable=False),
        sa.Column("ml_score", sa.Float(), nullable=False),
        sa.Column("event_score", sa.Float(), nullable=False),
        sa.Column("technical_score", sa.Float(), nullable=False),
        sa.Column("debate_consensus_score", sa.Float(), nullable=False),
        sa.Column("risk_adjusted_score", sa.Float(), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("artifact_uri", sa.String(length=1024), nullable=False),
        sa.Column("explanation_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prediction_artifacts_run_id", "prediction_artifacts", ["run_id"])
    op.create_index("ix_prediction_artifacts_symbol", "prediction_artifacts", ["symbol"])

    op.create_table(
        "recommendations",
        sa.Column("recommendation_id", sa.String(length=40), primary_key=True),
        sa.Column("run_id", sa.String(length=40), sa.ForeignKey("workflow_runs.run_id"), nullable=False),
        sa.Column("prediction_artifact_id", sa.String(length=40), sa.ForeignKey("prediction_artifacts.artifact_id"), nullable=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("action", recommendation_action_enum, nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("risk_flags_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recommendations_run_id", "recommendations", ["run_id"])
    op.create_index("ix_recommendations_symbol", "recommendations", ["symbol"])

    op.create_table(
        "trades",
        sa.Column("trade_id", sa.String(length=40), primary_key=True),
        sa.Column("run_id", sa.String(length=40), sa.ForeignKey("workflow_runs.run_id"), nullable=False),
        sa.Column("recommendation_id", sa.String(length=40), sa.ForeignKey("recommendations.recommendation_id"), nullable=True),
        sa.Column("recommendation_run_id", sa.String(length=40), sa.ForeignKey("workflow_runs.run_id"), nullable=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("fees", sa.Float(), nullable=False),
        sa.Column("screenshot_uri", sa.String(length=1024), nullable=False),
        sa.Column("ocr_raw_json", sa.JSON(), nullable=False),
        sa.Column("confirmation_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_trades_run_id", "trades", ["run_id"])
    op.create_index("ix_trades_symbol", "trades", ["symbol"])

    op.create_table(
        "review_reports",
        sa.Column("review_report_id", sa.String(length=40), primary_key=True),
        sa.Column("run_id", sa.String(length=40), sa.ForeignKey("workflow_runs.run_id"), nullable=False),
        sa.Column("target_run_id", sa.String(length=40), sa.ForeignKey("workflow_runs.run_id"), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("verdict_json", sa.JSON(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("knowledge_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_review_reports_run_id", "review_reports", ["run_id"])
    op.create_index("ix_review_reports_target_run_id", "review_reports", ["target_run_id"])
    op.create_index("ix_review_reports_as_of_date", "review_reports", ["as_of_date"])


def downgrade() -> None:
    op.drop_index("ix_review_reports_as_of_date", table_name="review_reports")
    op.drop_index("ix_review_reports_target_run_id", table_name="review_reports")
    op.drop_index("ix_review_reports_run_id", table_name="review_reports")
    op.drop_table("review_reports")

    op.drop_index("ix_trades_symbol", table_name="trades")
    op.drop_index("ix_trades_run_id", table_name="trades")
    op.drop_table("trades")

    op.drop_index("ix_recommendations_symbol", table_name="recommendations")
    op.drop_index("ix_recommendations_run_id", table_name="recommendations")
    op.drop_table("recommendations")

    op.drop_index("ix_prediction_artifacts_symbol", table_name="prediction_artifacts")
    op.drop_index("ix_prediction_artifacts_run_id", table_name="prediction_artifacts")
    op.drop_table("prediction_artifacts")

    op.drop_index("ix_feature_snapshots_symbol", table_name="feature_snapshots")
    op.drop_index("ix_feature_snapshots_as_of_date", table_name="feature_snapshots")
    op.drop_index("ix_feature_snapshots_run_id", table_name="feature_snapshots")
    op.drop_table("feature_snapshots")

    op.drop_index("ix_daily_briefs_as_of_date", table_name="daily_briefs")
    op.drop_index("ix_daily_briefs_run_id", table_name="daily_briefs")
    op.drop_table("daily_briefs")

    op.drop_index("ix_news_articles_published_at", table_name="news_articles")
    op.drop_table("news_articles")

    op.drop_index("ix_agent_node_runs_run_id", table_name="agent_node_runs")
    op.drop_table("agent_node_runs")

    op.drop_index("ix_workflow_runs_flow_type", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_as_of_date", table_name="workflow_runs")
    op.drop_table("workflow_runs")
