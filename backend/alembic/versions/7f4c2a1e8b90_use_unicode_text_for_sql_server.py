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


_COLUMNS = {
    "users": {"display_name": 255},
    "hospitals": {"hospital_code": 50, "hospital_name": 255, "notes": None},
    "hospital_aliases": {"alias": 255, "normalized_alias": 255},
    "manufacturers": {"name": 255},
    "equipment_types": {"name": 255},
    "equipment": {"equipment_code": 50, "equipment_name": 255, "model": 255, "serial_number": 255, "room_location": 255, "notes": None},
    "technicians": {"technician_code": 50, "display_name": 255},
}

_INDEXES = (
    ("hospitals", "ix_hospitals_hospital_code", ("hospital_code",), True),
    ("hospitals", "ix_hospitals_hospital_name", ("hospital_name",), False),
    ("hospital_aliases", "ix_hospital_aliases_normalized_alias", ("normalized_alias",), True),
    ("equipment", "ix_equipment_equipment_code", ("equipment_code",), True),
    ("equipment", "ix_equipment_hospital_name", ("hospital_id", "equipment_name"), False),
)

# Older schemas let SQL Server name single-column UNIQUE constraints.
_UNIQUE_KEYS = {
    "manufacturers": {"name"},
    "equipment_types": {"name"},
    "technicians": {"technician_code"},
    "equipment": {"serial_number"},
}


def _unique_constraints(bind, schema, table, changed_columns):
    if not (_UNIQUE_KEYS.get(table, set()) & changed_columns):
        return {}
    rows = bind.execute(sa.text("""
        SELECT k.name, c.name AS column_name
        FROM sys.key_constraints AS k
        JOIN sys.tables AS t ON t.object_id = k.parent_object_id
        JOIN sys.schemas AS s ON s.schema_id = t.schema_id
        JOIN sys.index_columns AS ic
          ON ic.object_id = t.object_id AND ic.index_id = k.unique_index_id
        JOIN sys.columns AS c ON c.object_id = t.object_id AND c.column_id = ic.column_id
        WHERE k.type = 'UQ' AND s.name = :schema AND t.name = :table
          AND ic.key_ordinal > 0
        ORDER BY k.name, ic.key_ordinal
    """), {"schema": schema, "table": table})
    constraints: dict[str, list[str]] = {}
    for name, column in rows:
        constraints.setdefault(name, []).append(column)
    return {name: columns for name, columns in constraints.items() if changed_columns.intersection(columns)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    schema = inspector.default_schema_name
    for table, targets in _COLUMNS.items():
        current = {column["name"]: column for column in inspector.get_columns(table, schema=schema)}
        # The initial revision creates from live metadata. Fresh databases can
        # already have these types and do not need their indexes rebuilt.
        changes = {}
        for column, length in targets.items():
            existing = current[column]["type"]
            collation = getattr(existing, "collation", None)
            new_type = sa.Unicode(length, collation=collation) if length else sa.UnicodeText(collation=collation)
            if existing.compile(dialect=bind.dialect) != new_type.compile(dialect=bind.dialect):
                changes[column] = new_type
        if not changes:
            continue
        indexes = [
            (name, columns, unique) for target, name, columns, unique in _INDEXES
            if target == table and changes.keys() & set(columns)
        ]
        constraints = _unique_constraints(bind, schema, table, set(changes))
        for name, _, _ in indexes:
            op.drop_index(name, table_name=table, schema=schema)
        for name in constraints:
            op.drop_constraint(name, table, type_="unique", schema=schema)
        for column, new_type in changes.items():
            op.alter_column(
                table, column, schema=schema, type_=new_type,
                existing_type=current[column]["type"],
                existing_nullable=current[column]["nullable"],
            )
        for name, columns in constraints.items():
            op.create_unique_constraint(name, table, columns, schema=schema)
        for name, columns, unique in indexes:
            op.create_index(name, table, list(columns), unique=unique, schema=schema)


def downgrade() -> None:
    raise RuntimeError("Downgrading Unicode columns could permanently lose stored text.")
