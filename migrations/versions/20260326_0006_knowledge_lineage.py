"""add lineage columns for knowledge tables

Revision ID: 20260326_0006
Revises: 20260326_0005
Create Date: 2026-03-26 13:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260326_0006'
down_revision = '20260326_0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('hot_knowledge', sa.Column('lineage_id', sa.String(length=40), nullable=True))
    op.add_column('cold_knowledge', sa.Column('lineage_id', sa.String(length=40), nullable=True))
    op.create_index('ix_hot_knowledge_lineage_id', 'hot_knowledge', ['lineage_id'], unique=False)
    op.create_index('ix_cold_knowledge_lineage_id', 'cold_knowledge', ['lineage_id'], unique=False)

    bind = op.get_bind()
    bind.execute(sa.text('UPDATE hot_knowledge SET lineage_id = knowledge_id WHERE lineage_id IS NULL'))
    bind.execute(
        sa.text(
            'UPDATE cold_knowledge '
            'SET lineage_id = COALESCE(lineage_id, source_hot_knowledge_id) '
            'WHERE lineage_id IS NULL'
        )
    )


def downgrade() -> None:
    op.drop_index('ix_cold_knowledge_lineage_id', table_name='cold_knowledge')
    op.drop_index('ix_hot_knowledge_lineage_id', table_name='hot_knowledge')
    op.drop_column('cold_knowledge', 'lineage_id')
    op.drop_column('hot_knowledge', 'lineage_id')
