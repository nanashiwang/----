"""review flow hot knowledge

Revision ID: 20260326_0002
Revises: 20260326_0001
Create Date: 2026-03-26 12:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260326_0002"
down_revision = "20260326_0001"
branch_labels = None
depends_on = None


knowledge_status_enum = sa.Enum("active", "archived", "degraded", name="knowledgestatus", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "hot_knowledge",
        sa.Column("knowledge_id", sa.String(length=40), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("source_run_ids", sa.JSON(), nullable=False),
        sa.Column("source_recommendation_ids", sa.JSON(), nullable=False),
        sa.Column("tests_survived", sa.Integer(), nullable=False),
        sa.Column("pass_count", sa.Integer(), nullable=False),
        sa.Column("fail_count", sa.Integer(), nullable=False),
        sa.Column("pass_rate", sa.Float(), nullable=False),
        sa.Column("status", knowledge_status_enum, nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_hot_knowledge_category", "hot_knowledge", ["category"])

    with op.batch_alter_table("review_reports") as batch_op:
        batch_op.add_column(sa.Column("horizon", sa.Integer(), nullable=False, server_default="5"))
        batch_op.alter_column("summary", new_column_name="summary_text", existing_type=sa.Text(), existing_nullable=False)
        batch_op.alter_column("verdict_json", new_column_name="verdicts_json", existing_type=sa.JSON(), existing_nullable=False)

    with op.batch_alter_table("review_reports") as batch_op:
        batch_op.alter_column("horizon", server_default=None, existing_type=sa.Integer(), existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("review_reports") as batch_op:
        batch_op.alter_column("verdicts_json", new_column_name="verdict_json", existing_type=sa.JSON(), existing_nullable=False)
        batch_op.alter_column("summary_text", new_column_name="summary", existing_type=sa.Text(), existing_nullable=False)
        batch_op.drop_column("horizon")

    op.drop_index("ix_hot_knowledge_category", table_name="hot_knowledge")
    op.drop_table("hot_knowledge")
