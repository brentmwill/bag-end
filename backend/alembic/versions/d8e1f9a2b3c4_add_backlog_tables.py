"""add backlog_items and backlog_archive

Revision ID: d8e1f9a2b3c4
Revises: f7c2a8e1b4d6
Create Date: 2026-05-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd8e1f9a2b3c4'
down_revision: Union[str, None] = 'f7c2a8e1b4d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'backlog_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('area', sa.Text(), nullable=False),
        sa.Column('severity', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('repro_or_context', sa.Text(), nullable=True),
        sa.Column('proposed_fix', sa.Text(), nullable=True),
        sa.Column('created_by_persona', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_backlog_items_area', 'backlog_items', ['area'])
    op.create_index('ix_backlog_items_severity', 'backlog_items', ['severity'])

    op.create_table(
        'backlog_archive',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('area', sa.Text(), nullable=False),
        sa.Column('severity', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('repro_or_context', sa.Text(), nullable=True),
        sa.Column('proposed_fix', sa.Text(), nullable=True),
        sa.Column('created_by_persona', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolution', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('backlog_archive')
    op.drop_index('ix_backlog_items_severity', table_name='backlog_items')
    op.drop_index('ix_backlog_items_area', table_name='backlog_items')
    op.drop_table('backlog_items')
