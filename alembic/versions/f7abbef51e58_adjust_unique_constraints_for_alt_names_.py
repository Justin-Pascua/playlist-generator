"""Adjust unique constraints for alt_names and song_links

Revision ID: f7abbef51e58
Revises: 5432006b37aa
Create Date: 2026-01-15 19:32:35.827491

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7abbef51e58'
down_revision: Union[str, Sequence[str], None] = '5432006b37aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.drop_index(op.f('title'), table_name='alt_names')
    op.create_unique_constraint('alt_canonical_user_triple', 'alt_names', ['title', 'canonical_id', 'user_id'])
    
    op.drop_index(op.f('link'), table_name='song_links')
    op.create_unique_constraint(None, 'song_links', ['song_id', 'user_id'])


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint(None, 'song_links', type_='unique')
    op.create_index(op.f('link'), 'song_links', ['link'], unique=True)

    op.drop_constraint('alt_canonical_user_triple', 'alt_names', type_='unique')
    op.create_index(op.f('title'), 'alt_names', ['title'], unique=True)
