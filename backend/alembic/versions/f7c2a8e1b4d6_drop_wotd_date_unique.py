"""drop unique constraint on word_of_day_cache.date

Replaced rows from manual regen need to coexist alongside the active row
so their words remain in the dedupe exclude list.

Revision ID: f7c2a8e1b4d6
Revises: a1b2c3d4e5f6
Create Date: 2026-05-02

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'f7c2a8e1b4d6'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('word_of_day_cache_date_key', 'word_of_day_cache', type_='unique')
    op.create_index(
        'ix_word_of_day_cache_date',
        'word_of_day_cache',
        ['date'],
    )


def downgrade() -> None:
    op.drop_index('ix_word_of_day_cache_date', table_name='word_of_day_cache')
    op.create_unique_constraint('word_of_day_cache_date_key', 'word_of_day_cache', ['date'])
