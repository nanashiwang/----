"""taxonomy tag columns for knowledge tables

Revision ID: 20260326_0004
Revises: 20260326_0003
Create Date: 2026-03-26 21:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260326_0004"
down_revision = "20260326_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("hot_knowledge") as batch_op:
        batch_op.add_column(sa.Column("applicable_event_tags", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("applicable_technical_tags", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("applicable_market_regimes", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("negative_match_tags", sa.JSON(), nullable=False, server_default="[]"))

    with op.batch_alter_table("cold_knowledge") as batch_op:
        batch_op.add_column(sa.Column("applicable_event_tags", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("applicable_technical_tags", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("negative_match_tags", sa.JSON(), nullable=False, server_default="[]"))

    with op.batch_alter_table("hot_knowledge") as batch_op:
        batch_op.alter_column("applicable_event_tags", server_default=None)
        batch_op.alter_column("applicable_technical_tags", server_default=None)
        batch_op.alter_column("applicable_market_regimes", server_default=None)
        batch_op.alter_column("negative_match_tags", server_default=None)

    with op.batch_alter_table("cold_knowledge") as batch_op:
        batch_op.alter_column("applicable_event_tags", server_default=None)
        batch_op.alter_column("applicable_technical_tags", server_default=None)
        batch_op.alter_column("negative_match_tags", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("cold_knowledge") as batch_op:
        batch_op.drop_column("negative_match_tags")
        batch_op.drop_column("applicable_technical_tags")
        batch_op.drop_column("applicable_event_tags")

    with op.batch_alter_table("hot_knowledge") as batch_op:
        batch_op.drop_column("negative_match_tags")
        batch_op.drop_column("applicable_market_regimes")
        batch_op.drop_column("applicable_technical_tags")
        batch_op.drop_column("applicable_event_tags")
