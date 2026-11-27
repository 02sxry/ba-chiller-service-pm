"""Preserve Thai messages, notes and audit text.

Revision ID: a1c2d3e4f570
Revises: 7f4c2a1e8b90
"""

import sqlalchemy as sa
from alembic import op

revision = "a1c2d3e4f570"
down_revision = "7f4c2a1e8b90"

_COLUMNS = {
    "appointment_revisions": {"service_type": 100, "requested_by": 255, "notes": None, "reason": None},
    "audit_logs": {"actor_label": 255, "reason": None},
    "drive_files": {"original_name": 500},
    "master_data_drafts": {"original_text": None, "review_notes": None},
    "notification_jobs": {"last_error": None},
    "reschedule_requests": {"message": None},
    "schedule_intakes": {"raw_text": None},
    "sync_events": {"last_error": None},
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    schema = inspector.default_schema_name
    for table, targets in _COLUMNS.items():
        columns = {column["name"]: column for column in inspector.get_columns(table, schema=schema)}
        for column, length in targets.items():
            current = columns[column]
            collation = getattr(current["type"], "collation", None)
            new_type = sa.Unicode(length, collation=collation) if length else sa.UnicodeText(collation=collation)
            if current["type"].compile(dialect=bind.dialect) != new_type.compile(dialect=bind.dialect):
                op.alter_column(
                    table, column, schema=schema, type_=new_type,
                    existing_type=current["type"], existing_nullable=current["nullable"],
                )


def downgrade() -> None:
    raise RuntimeError("Downgrading Unicode columns could permanently lose stored text.")
