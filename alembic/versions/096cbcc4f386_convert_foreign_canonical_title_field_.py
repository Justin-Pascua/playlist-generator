"""Convert foreign canonical title field to canonical id

Revision ID: 096cbcc4f386
Revises: d9ce6eedd05e
Create Date: 2026-01-14 11:18:09.171808

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '096cbcc4f386'
down_revision: Union[str, Sequence[str], None] = 'd9ce6eedd05e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column('alt_names', sa.Column('canonical_id', sa.Integer(), nullable=False))
    op.drop_column('alt_names', 'canonical')

    op.add_column('song_links', sa.Column('song_id', sa.Integer(), nullable=False))
    op.drop_index(op.f('song_title'), table_name='song_links')
    op.create_unique_constraint(None, 'song_links', ['song_id'])
    op.drop_column('song_links', 'song_title')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('song_links', sa.Column('song_title', mysql.VARCHAR(length=64), nullable=False))
    op.drop_constraint(None, 'song_links', type_='unique')
    op.create_index(op.f('song_title'), 'song_links', ['song_title'], unique=True)
    op.drop_column('song_links', 'song_id')
    
    op.add_column('alt_names', sa.Column('canonical', mysql.VARCHAR(length=64), nullable=False))
    op.drop_column('alt_names', 'canonical_id')