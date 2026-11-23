import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.enums import SyncStatus
from app.domain.models import Hospital, SyncEvent, User
from app.integrations.google import GoogleWorkspaceProvider
from app.services.audit import record_audit


class SyncError(ValueError):
    pass


def _submission_key(worksheet: str, row: dict[str, Any]) -> str:
    canonical = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return f"sheet-in:{worksheet}:{row.get('row_key')}:{digest}"


def _queue_hospital_export(db: Session, hospital: Hospital) -> SyncEvent:
    event = SyncEvent(
        idempotency_key=f"sheet-out:hospital:{hospital.id}:v{hospital.version}",
        direction="OUTBOUND",
        entity_type="Hospitals_View",
        entity_id=hospital.id,
        payload={
            "worksheet": "Hospitals_View",
            "rows": [{
                "record_id": str(hospital.id),
                "hospital_code": hospital.hospital_code,
                "hospital_name": hospital.hospital_name,
                "short_name": hospital.short_name,
                "active": hospital.active,
                "version": hospital.version,
            }],
        },
        expected_version=hospital.version,
        status=SyncStatus.PENDING,
    )
    db.add(event)
    return event


def process_hospital_submission(
    db: Session,
    row: dict[str, Any],
    admin: User,
) -> SyncEvent:
    row_key = str(row.get("row_key") or "").strip()
    if not row_key:
        raise SyncError("row_key จำเป็นและห้ามใช้ตำแหน่งแถวแทน")
    idempotency_key = _submission_key("Hospitals_Input", row)
    existing = db.scalar(select(SyncEvent).where(SyncEvent.idempotency_key == idempotency_key))
    if existing:
        return existing
    event = SyncEvent(
        idempotency_key=idempotency_key,
        direction="INBOUND",
        entity_type="Hospital",
        payload=row,
        expected_version=row.get("expected_version"),
        status=SyncStatus.PROCESSING,
    )
    db.add(event)
    db.flush()
    operation = str(row.get("operation") or "").upper()
    try:
        if operation == "CREATE":
            if row.get("record_id"):
                raise SyncError("CREATE ต้องไม่มี record_id")
            hospital = Hospital(
                hospital_code=str(row.get("hospital_code") or "").strip(),
                hospital_name=str(row.get("hospital_name") or "").strip(),
                short_name=str(row["short_name"]).strip() if row.get("short_name") else None,
                notes=str(row["notes"]).strip() if row.get("notes") else None,
            )
            if not hospital.hospital_code or not hospital.hospital_name:
                raise SyncError("hospital_code และ hospital_name จำเป็น")
            with db.begin_nested():
                db.add(hospital)
                db.flush()
            event.entity_id = hospital.id
            record_audit(
                db,
                actor=admin,
                action="GOOGLE_HOSPITAL_CREATED",
                entity_type="hospital",
                entity_id=hospital.id,
                new_values={"hospital_code": hospital.hospital_code, "hospital_name": hospital.hospital_name},
                source="GOOGLE_SHEETS",
            )
        elif operation in {"UPDATE", "DEACTIVATE"}:
            try:
                record_id = uuid.UUID(str(row.get("record_id")))
            except ValueError as exc:
                raise SyncError("record_id ไม่ถูกต้อง") from exc
            hospital = db.scalar(select(Hospital).where(Hospital.id == record_id).with_for_update())
            if not hospital:
                raise SyncError("ไม่พบ hospital record")
            expected_version = row.get("expected_version")
            if expected_version is None or int(expected_version) != hospital.version:
                event.status = SyncStatus.CONFLICT
                event.entity_id = hospital.id
                event.last_error = f"version ปัจจุบันคือ {hospital.version} แต่ submission ใช้ {expected_version}"
                return event
            old_values = {
                "hospital_name": hospital.hospital_name,
                "short_name": hospital.short_name,
                "active": hospital.active,
                "version": hospital.version,
            }
            if operation == "DEACTIVATE":
                hospital.active = False
            else:
                hospital.hospital_name = str(row.get("hospital_name") or hospital.hospital_name).strip()
                hospital.short_name = str(row["short_name"]).strip() if row.get("short_name") else None
                hospital.notes = str(row["notes"]).strip() if row.get("notes") else hospital.notes
            db.flush()
            event.entity_id = hospital.id
            record_audit(
                db,
                actor=admin,
                action=f"GOOGLE_HOSPITAL_{operation}",
                entity_type="hospital",
                entity_id=hospital.id,
                old_values=old_values,
                new_values={
                    "hospital_name": hospital.hospital_name,
                    "short_name": hospital.short_name,
                    "active": hospital.active,
                    "version": hospital.version,
                },
                source="GOOGLE_SHEETS",
            )
        else:
            raise SyncError("operation ต้องเป็น CREATE, UPDATE หรือ DEACTIVATE")
        event.status = SyncStatus.APPLIED
        _queue_hospital_export(db, hospital)
        return event
    except IntegrityError as exc:
        event.status = SyncStatus.FAILED
        event.last_error = "ข้อมูลซ้ำหรือขัดกับ database constraint"
        event.payload = {**event.payload, "database_error": type(exc.orig).__name__}
        return event
    except SyncError as exc:
        event.status = SyncStatus.FAILED
        event.last_error = str(exc)
        return event


def process_outbound_event(
    db: Session,
    event: SyncEvent,
    provider: GoogleWorkspaceProvider,
    *,
    max_attempts: int = 5,
) -> SyncEvent:
    if event.direction != "OUTBOUND" or event.status not in {SyncStatus.PENDING, SyncStatus.FAILED}:
        raise SyncError("sync event ไม่อยู่ในสถานะที่ส่งออกได้")
    event.status = SyncStatus.PROCESSING
    event.attempts += 1
    result = provider.export_rows(event.payload["worksheet"], event.payload["rows"])
    if result.success:
        event.status = SyncStatus.APPLIED
        event.last_error = None
    else:
        event.last_error = result.error or "Google provider error"
        event.status = SyncStatus.FAILED if event.attempts >= max_attempts else SyncStatus.PENDING
    return event
