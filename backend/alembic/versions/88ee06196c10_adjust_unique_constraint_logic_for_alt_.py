"""Adjust unique constraint logic for alt_names table

Revision ID: 88ee06196c10
Revises: f0b9a30c1559
Create Date: 2026-01-23 17:10:06.002696

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88ee06196c10'
down_revision: Union[str, Sequence[str], None] = 'f0b9a30c1559'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.drop_index(op.f('alt_canonical_user_triple'), table_name='alt_names')
    op.create_unique_constraint('alt_and_user', 'alt_names', ['title', 'user_id'])
    

def downgrade() -> None:
    """Downgrade schema."""
    
    op.drop_constraint('alt_and_user', 'alt_names', type_='unique')
    op.create_index(op.f('alt_canonical_user_triple'), 'alt_names', ['title', 'canonical_id', 'user_id'], unique=True)
    