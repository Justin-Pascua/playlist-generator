"""Add cascade property to relationships

Revision ID: 5432006b37aa
Revises: e6f09ff315c3
Create Date: 2026-01-15 18:48:03.511429

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5432006b37aa'
down_revision: Union[str, Sequence[str], None] = 'e6f09ff315c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.drop_constraint(op.f('alt_names_ibfk_2'), 'alt_names', type_='foreignkey')
    op.drop_constraint(op.f('alt_names_ibfk_1'), 'alt_names', type_='foreignkey')
    
    op.create_foreign_key(None, 'alt_names', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'alt_names', 'canonical_names', ['canonical_id'], ['id'], ondelete='CASCADE')
    
    op.drop_constraint(op.f('canonical_names_ibfk_1'), 'canonical_names', type_='foreignkey')
    op.create_foreign_key(None, 'canonical_names', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    
    op.drop_constraint(op.f('playlists_ibfk_1'), 'playlists', type_='foreignkey')
    op.create_foreign_key(None, 'playlists', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    
    op.drop_constraint(op.f('song_links_ibfk_1'), 'song_links', type_='foreignkey')
    op.drop_constraint(op.f('song_links_ibfk_2'), 'song_links', type_='foreignkey')
    op.create_foreign_key(None, 'song_links', 'canonical_names', ['song_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'song_links', 'users', ['user_id'], ['id'], ondelete='CASCADE')



def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'song_links', type_='foreignkey')
    op.drop_constraint(None, 'song_links', type_='foreignkey')
    op.create_foreign_key(op.f('song_links_ibfk_2'), 'song_links', 'users', ['user_id'], ['id'])
    op.create_foreign_key(op.f('song_links_ibfk_1'), 'song_links', 'canonical_names', ['song_id'], ['id'])
    
    op.drop_constraint(None, 'playlists', type_='foreignkey')
    op.create_foreign_key(op.f('playlists_ibfk_1'), 'playlists', 'users', ['user_id'], ['id'])
    
    op.drop_constraint(None, 'canonical_names', type_='foreignkey')
    op.create_foreign_key(op.f('canonical_names_ibfk_1'), 'canonical_names', 'users', ['user_id'], ['id'])
    
    op.drop_constraint(None, 'alt_names', type_='foreignkey')
    op.drop_constraint(None, 'alt_names', type_='foreignkey')
    op.create_foreign_key(op.f('alt_names_ibfk_1'), 'alt_names', 'canonical_names', ['canonical_id'], ['id'])
    op.create_foreign_key(op.f('alt_names_ibfk_2'), 'alt_names', 'users', ['user_id'], ['id'])
