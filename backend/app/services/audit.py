import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from app.domain.models import AuditLog, User


def _json_safe(value: Any) -> Any:
    if isinstance(value, (uuid.UUID, datetime, date)):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


def record_audit(
    db: Session,
    *,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    reason: str | None = None,
    source: str = "WEB",
    revision_number: int | None = None,
    actor_label: str | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_id=actor.id if actor else None,
        actor_label=actor_label,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=_json_safe(old_values) if old_values is not None else None,
        new_values=_json_safe(new_values) if new_values is not None else None,
        reason=reason,
        source=source,
        revision_number=revision_number,
    )
    db.add(log)
    return log

