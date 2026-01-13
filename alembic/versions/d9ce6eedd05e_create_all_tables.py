"""Create all tables

Revision ID: d9ce6eedd05e
Revises: 
Create Date: 2026-01-13 12:42:45.058132

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9ce6eedd05e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('canonical_names',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('title')
    )
    op.create_table('alt_names',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=64), nullable=False),
        sa.Column('canonical', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('title')
    )

    op.create_table('playlists',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('playlist_title', sa.String(length=64), nullable=True),
        sa.Column('link', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('link')
    )

    op.create_table('song_links',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('song_title', sa.String(length=64), nullable=False),
        sa.Column('link', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('link'),
        sa.UniqueConstraint('song_title')
    )

    op.create_table('users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=64), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('password', sa.String(length=64), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('users')
    op.drop_table('song_links')
    op.drop_table('playlists')
    op.drop_table('alt_names')
    