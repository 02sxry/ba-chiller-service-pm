"""add usernames for application login

Revision ID: 3e7b1a9c4d21
Revises: 1b6004596e27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3e7b1a9c4d21"
down_revision: Union[str, None] = "1b6004596e27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=100), nullable=True))
    op.execute("UPDATE users SET username = lower(email) WHERE username IS NULL")
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "username")
