"""ml experiment records

Revision ID: 20260326_0005
Revises: 20260326_0004
Create Date: 2026-03-26 22:10:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260326_0005"
down_revision = "20260326_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ml_experiments",
        sa.Column("experiment_id", sa.String(length=40), primary_key=True),
        sa.Column("experiment_group_id", sa.String(length=40), nullable=False),
        sa.Column("experiment_mode", sa.String(length=20), nullable=False),
        sa.Column("dataset_version", sa.String(length=50), nullable=False),
        sa.Column("feature_set_version", sa.String(length=50), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=50), nullable=False),
        sa.Column("tag_encoder_version", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=80), nullable=False),
        sa.Column("label_horizon", sa.Integer(), nullable=False),
        sa.Column("cv_method", sa.String(length=50), nullable=False),
        sa.Column("artifact_path", sa.String(length=1024), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("params_json", sa.JSON(), nullable=False),
        sa.Column("shap_summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ml_experiments_experiment_group_id", "ml_experiments", ["experiment_group_id"])
    op.create_index("ix_ml_experiments_experiment_mode", "ml_experiments", ["experiment_mode"])


def downgrade() -> None:
    op.drop_index("ix_ml_experiments_experiment_mode", table_name="ml_experiments")
    op.drop_index("ix_ml_experiments_experiment_group_id", table_name="ml_experiments")
    op.drop_table("ml_experiments")
