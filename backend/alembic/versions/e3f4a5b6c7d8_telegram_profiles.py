"""add telegram_user_id, dob to user_profiles; add static_preferences

Revision ID: e3f4a5b6c7d8
Revises: c1a2b3d4e5f6
Create Date: 2026-04-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, None] = 'c1a2b3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_profiles', sa.Column('telegram_user_id', sa.BigInteger(), nullable=True))
    op.add_column('user_profiles', sa.Column('dob', sa.Date(), nullable=True))
    op.create_unique_constraint('uq_user_profiles_telegram_user_id', 'user_profiles', ['telegram_user_id'])

    op.create_table(
        'static_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pref_type', sa.Text(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_profile_id'], ['user_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('static_preferences')
    op.drop_constraint('uq_user_profiles_telegram_user_id', 'user_profiles', type_='unique')
    op.drop_column('user_profiles', 'dob')
    op.drop_column('user_profiles', 'telegram_user_id')
