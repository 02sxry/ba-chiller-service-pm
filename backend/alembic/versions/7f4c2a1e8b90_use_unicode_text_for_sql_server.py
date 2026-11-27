"""store user-entered Thai text as Unicode on SQL Server

Revision ID: 7f4c2a1e8b90
Revises: 3e7b1a9c4d21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f4c2a1e8b90"
down_revision: Union[str, None] = "3e7b1a9c4d21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_UNICODE_COLUMNS = (
    ("users", "display_name", 255, False),
    ("hospitals", "hospital_code", 50, False),
    ("hospitals", "hospital_name", 255, False),
    ("hospital_aliases", "alias", 255, False),
    ("hospital_aliases", "normalized_alias", 255, False),
    ("manufacturers", "name", 255, False),
    ("equipment_types", "name", 255, False),
    ("equipment", "equipment_code", 50, False),
    ("equipment", "equipment_name", 255, False),
    ("equipment", "model", 255, True),
    ("equipment", "serial_number", 255, True),
    ("equipment", "room_location", 255, True),
    ("technicians", "technician_code", 50, False),
    ("technicians", "display_name", 255, False),
)

_TEXT_COLUMNS = (
    ("hospitals", "notes"),
    ("equipment", "notes"),
)


def upgrade() -> None:
    for table, column, length, nullable in _UNICODE_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.Unicode(length=length),
            existing_type=sa.String(length=length),
            existing_nullable=nullable,
        )
    for table, column in _TEXT_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.UnicodeText(),
            existing_type=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    for table, column in ("hospitals", "notes"), ("equipment", "notes"):
        op.alter_column(
            table,
            column,
            type_=sa.Text(),
            existing_type=sa.UnicodeText(),
            existing_nullable=True,
        )
    for table, column, length, nullable in reversed(_UNICODE_COLUMNS):
        op.alter_column(
            table,
            column,
            type_=sa.String(length=length),
            existing_type=sa.Unicode(length=length),
            existing_nullable=nullable,
        )
