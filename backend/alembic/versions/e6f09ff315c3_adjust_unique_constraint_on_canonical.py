"""Adjust unique constraint on Canonical

Revision ID: e6f09ff315c3
Revises: b8bf21a0867d
Create Date: 2026-01-15 12:02:39.900629

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6f09ff315c3'
down_revision: Union[str, Sequence[str], None] = 'b8bf21a0867d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.drop_index(op.f('title'), table_name='canonical_names')
    op.create_unique_constraint('title_user_pair', 'canonical_names', ['title', 'user_id'])
    

def downgrade() -> None:
    """Downgrade schema."""
    
    op.drop_constraint('title_user_pair', 'canonical_names', type_='unique')
    op.create_index(op.f('title'), 'canonical_names', ['title'], unique=True)
    