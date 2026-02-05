"""Create foreign keys

Revision ID: 7046cae25f9c
Revises: 096cbcc4f386
Create Date: 2026-01-14 12:22:02.710114

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7046cae25f9c'
down_revision: Union[str, Sequence[str], None] = '096cbcc4f386'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_foreign_key(None, 'alt_names', 'canonical_names', ['canonical_id'], ['id'])
    op.create_foreign_key(None, 'alt_names', 'users', ['user_id'], ['id'])

    op.create_foreign_key(None, 'canonical_names', 'users', ['user_id'], ['id'])
    
    op.create_foreign_key(None, 'playlists', 'users', ['user_id'], ['id'])
    
    op.create_foreign_key(None, 'song_links', 'canonical_names', ['song_id'], ['id'])
    op.create_foreign_key(None, 'song_links', 'users', ['user_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'song_links', type_='foreignkey')
    op.drop_constraint(None, 'song_links', type_='foreignkey')
    
    op.drop_constraint(None, 'playlists', type_='foreignkey')
    
    op.drop_constraint(None, 'canonical_names', type_='foreignkey')
    
    op.drop_constraint(None, 'alt_names', type_='foreignkey')
    op.drop_constraint(None, 'alt_names', type_='foreignkey')
