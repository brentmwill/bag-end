"""add notes to meal_plan_slots

Revision ID: c1a2b3d4e5f6
Revises: b3f1e2a4c7d9
Create Date: 2026-04-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, None] = 'b3f1e2a4c7d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('meal_plan_slots', sa.Column('notes', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('meal_plan_slots', 'notes')
