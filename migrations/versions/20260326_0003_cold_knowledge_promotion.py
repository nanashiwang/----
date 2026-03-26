"""cold knowledge promotion tables

Revision ID: 20260326_0003
Revises: 20260326_0002
Create Date: 2026-03-26 18:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260326_0003"
down_revision = "20260326_0002"
branch_labels = None
depends_on = None


knowledge_status_enum = sa.Enum("active", "archived", "degraded", name="knowledgestatus", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "cold_knowledge",
        sa.Column("knowledge_id", sa.String(length=40), primary_key=True),
        sa.Column(
            "source_hot_knowledge_id",
            sa.String(length=40),
            sa.ForeignKey("hot_knowledge.knowledge_id"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("promotion_reason", sa.Text(), nullable=False),
        sa.Column(
            "promotion_run_id",
            sa.String(length=40),
            sa.ForeignKey("workflow_runs.run_id"),
            nullable=False,
        ),
        sa.Column("source_run_ids", sa.JSON(), nullable=False),
        sa.Column("source_recommendation_ids", sa.JSON(), nullable=False),
        sa.Column("tests_survived", sa.Integer(), nullable=False),
        sa.Column("pass_count", sa.Integer(), nullable=False),
        sa.Column("fail_count", sa.Integer(), nullable=False),
        sa.Column("pass_rate", sa.Float(), nullable=False),
        sa.Column("applicable_market_regimes", sa.JSON(), nullable=False),
        sa.Column("invalid_conditions", sa.JSON(), nullable=False),
        sa.Column("status", knowledge_status_enum, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cold_knowledge_source_hot_knowledge_id", "cold_knowledge", ["source_hot_knowledge_id"])
    op.create_index("ix_cold_knowledge_promotion_run_id", "cold_knowledge", ["promotion_run_id"])
    op.create_index("ix_cold_knowledge_category", "cold_knowledge", ["category"])

    op.create_table(
        "knowledge_events",
        sa.Column("event_id", sa.String(length=40), primary_key=True),
        sa.Column("knowledge_id", sa.String(length=40), nullable=False),
        sa.Column("knowledge_type", sa.String(length=20), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("source_run_id", sa.String(length=40), sa.ForeignKey("workflow_runs.run_id"), nullable=True),
        sa.Column(
            "source_review_report_id",
            sa.String(length=40),
            sa.ForeignKey("review_reports.review_report_id"),
            nullable=True,
        ),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_knowledge_events_knowledge_id", "knowledge_events", ["knowledge_id"])
    op.create_index("ix_knowledge_events_knowledge_type", "knowledge_events", ["knowledge_type"])
    op.create_index("ix_knowledge_events_event_type", "knowledge_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_events_event_type", table_name="knowledge_events")
    op.drop_index("ix_knowledge_events_knowledge_type", table_name="knowledge_events")
    op.drop_index("ix_knowledge_events_knowledge_id", table_name="knowledge_events")
    op.drop_table("knowledge_events")

    op.drop_index("ix_cold_knowledge_category", table_name="cold_knowledge")
    op.drop_index("ix_cold_knowledge_promotion_run_id", table_name="cold_knowledge")
    op.drop_index("ix_cold_knowledge_source_hot_knowledge_id", table_name="cold_knowledge")
    op.drop_table("cold_knowledge")
