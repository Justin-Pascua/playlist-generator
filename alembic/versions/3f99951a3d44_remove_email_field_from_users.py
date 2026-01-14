"""Remove email field from users

Revision ID: 3f99951a3d44
Revises: 7046cae25f9c
Create Date: 2026-01-14 13:50:22.412765

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '3f99951a3d44'
down_revision: Union[str, Sequence[str], None] = '7046cae25f9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f('email'), table_name='users')
    op.drop_column('users', 'email')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('users', sa.Column('email', mysql.VARCHAR(length=64), nullable=False))
    op.create_index(op.f('email'), 'users', ['email'], unique=True)
