"""add conversation_log and food_log

Revision ID: b5c4a3d2e1f0
Revises: d8e1f9a2b3c4
Create Date: 2026-05-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b5c4a3d2e1f0'
down_revision: Union[str, None] = 'd8e1f9a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'conversation_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('user_profile_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('direction', sa.Text(), nullable=False),
        sa.Column('persona', sa.Text(), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_profile_id'], ['user_profiles.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_conversation_log_tg_user_time',
        'conversation_log',
        ['telegram_user_id', 'created_at'],
    )

    op.create_table(
        'food_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('eaten_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recipe_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('freeform_description', sa.Text(), nullable=True),
        sa.Column('grams', sa.Integer(), nullable=True),
        sa.Column('est_calories', sa.Integer(), nullable=True),
        sa.Column('est_macros', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            'recipe_id IS NOT NULL OR freeform_description IS NOT NULL',
            name='ck_food_log_recipe_or_description',
        ),
        sa.ForeignKeyConstraint(['user_profile_id'], ['user_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_food_log_user_time',
        'food_log',
        ['user_profile_id', 'eaten_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_food_log_user_time', table_name='food_log')
    op.drop_table('food_log')
    op.drop_index('ix_conversation_log_tg_user_time', table_name='conversation_log')
    op.drop_table('conversation_log')
