"""Adjust video unique constraint

Revision ID: ce105a77ad37
Revises: 88ee06196c10
Create Date: 2026-01-29 10:26:18.353003

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce105a77ad37'
down_revision: Union[str, Sequence[str], None] = '88ee06196c10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f('id'), table_name='videos')
    op.create_unique_constraint(None, 'videos', ['canonical_name_id', 'user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'videos', type_='unique')
    op.create_index(op.f('id'), 'videos', ['id', 'user_id'], unique=True)
