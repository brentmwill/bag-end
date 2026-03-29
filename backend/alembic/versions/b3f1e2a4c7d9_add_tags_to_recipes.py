"""add tags to recipes

Revision ID: b3f1e2a4c7d9
Revises: 4ebc44c9fcc6
Create Date: 2026-03-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b3f1e2a4c7d9'
down_revision: Union[str, None] = '4ebc44c9fcc6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('recipes', sa.Column(
        'tags',
        postgresql.ARRAY(sa.String()),
        server_default='{}',
        nullable=False,
    ))


def downgrade() -> None:
    op.drop_column('recipes', 'tags')
