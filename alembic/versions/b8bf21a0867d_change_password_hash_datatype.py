"""Change password hash datatype

Revision ID: b8bf21a0867d
Revises: 3f99951a3d44
Create Date: 2026-01-14 14:10:35.195624

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'b8bf21a0867d'
down_revision: Union[str, Sequence[str], None] = '3f99951a3d44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('users', 'password',
               existing_type=mysql.VARCHAR(length=64),
               type_=sa.String(length=256),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'password',
               existing_type=sa.String(length=256),
               type_=mysql.VARCHAR(length=64),
               existing_nullable=False)
