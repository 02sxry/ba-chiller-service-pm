import hashlib
import secrets
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import bool_filter, lock_query
from app.domain.enums import AppointmentStatus, ChangeSource, NotificationStatus
from app.domain.models import (
    ActionToken,
    Appointment,
    AppointmentRevision,
    Equipment,
    LineGroupMapping,
    NotificationJob,
    PMSlot,
    RescheduleRequest,
    User,
)
from app.domain.schemas import AppointmentApproveRequest, DateChangeRequest
from app.services.audit import record_audit


class AppointmentError(ValueError):
    pass


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _queue_notification(
    db: Session,
    *,
    kind: str,
    destination_id: str,
    appointment: Appointment,
    revision: AppointmentRevision,
    action_token: str | None = None,
) -> NotificationJob:
    equipment = db.get(Equipment, appointment.equipment_id)
    actions = None
    if action_token:
        actions = {
            "confirm": f"action=confirm&token={action_token}",
            "reschedule": f"action=reschedule&token={action_token}",
        }
    job = NotificationJob(
        idempotency_key=f"{kind}:{appointment.id}:{revision.id}",
        kind=kind,
        destination_id=destination_id,
        appointment_id=appointment.id,
        revision_id=revision.id,
        payload={
            "appointment_id": str(appointment.id),
            "revision_id": str(revision.id),
            "scheduled_date": revision.scheduled_date.isoformat(),
            "service_type": revision.service_type,
            "equipment_name": equipment.equipment_name if equipment else None,
            "room_location": equipment.room_location if equipment else None,
            "actions": actions,
        },
        status=NotificationStatus.PENDING,
    )
    db.add(job)
    return job


def approve_appointment(db: Session, request: AppointmentApproveRequest, admin: User) -> tuple[Appointment, str]:
    slot = db.scalar(lock_query(select(PMSlot).where(PMSlot.id == request.pm_slot_id), PMSlot, db))
    if not slot or not slot.active:
        raise AppointmentError("ไม่พบ PM Slot ที่ใช้งานอยู่")
    if slot.version != request.expected_slot_version:
        raise AppointmentError("PM Slot ถูกแก้ไขแล้ว กรุณาโหลดข้อมูลใหม่")
    if slot.equipment_id != request.equipment_id:
        raise AppointmentError("อุปกรณ์ไม่ตรงกับ PM Slot")
    equipment = db.get(Equipment, request.equipment_id)
    if not equipment or equipment.hospital_id != request.hospital_id:
        raise AppointmentError("โรงพยาบาลไม่ตรงกับอุปกรณ์")
    existing = db.scalar(select(Appointment).where(Appointment.pm_slot_id == slot.id))
    if existing:
        raise AppointmentError("PM Slot นี้มีนัดอยู่แล้ว ให้ใช้ขั้นตอนแก้ไขนัด")
    mapping = db.scalar(
        select(LineGroupMapping).where(
            LineGroupMapping.hospital_id == request.hospital_id,
            LineGroupMapping.group_type == "HOSPITAL",
            bool_filter(LineGroupMapping.active, True),
        )
    )
    if not mapping:
        raise AppointmentError("ยังไม่ได้ลงทะเบียน LINE group ของโรงพยาบาล")
    appointment = Appointment(
        pm_slot_id=slot.id,
        hospital_id=request.hospital_id,
        equipment_id=request.equipment_id,
        technician_id=request.technician_id,
        status=AppointmentStatus.PENDING_CONFIRMATION,
    )
    db.add(appointment)
    db.flush()
    revision = AppointmentRevision(
        appointment_id=appointment.id,
        revision_number=1,
        scheduled_date=request.scheduled_date,
        service_type=request.service_type,
        notes=request.notes,
        change_source=ChangeSource.ADMIN,
        approved_by_id=admin.id,
    )
    db.add(revision)
    db.flush()
    appointment.current_revision_id = revision.id
    raw_token = secrets.token_urlsafe(32)
    db.add(ActionToken(
        token_hash=_hash_token(raw_token),
        appointment_id=appointment.id,
        revision_id=revision.id,
        action="CONFIRM_OR_RESCHEDULE",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    ))
    _queue_notification(
        db, kind="APPOINTMENT_PROPOSAL", destination_id=mapping.line_group_id,
        appointment=appointment, revision=revision, action_token=raw_token,
    )
    record_audit(
        db, actor=admin, action="APPOINTMENT_APPROVED", entity_type="appointment",
        entity_id=appointment.id, new_values={"date": request.scheduled_date.isoformat(), "slot_id": str(slot.id)},
        revision_number=1,
    )
    try:
        db.flush()
    except IntegrityError as exc:
        raise AppointmentError("ไม่สามารถสร้างนัดซ้ำใน PM Slot เดียวกัน") from exc
    return appointment, raw_token


def _validate_action_token(
    db: Session,
    token: str,
    line_group_id: str,
    allowed_actions: set[str],
) -> tuple[ActionToken, Appointment, AppointmentRevision]:
    action_token = db.scalar(
        lock_query(select(ActionToken).where(ActionToken.token_hash == _hash_token(token)), ActionToken, db)
    )
    if not action_token or action_token.used_at or action_token.expires_at <= datetime.now(UTC):
        raise AppointmentError("ลิงก์ตอบรับไม่ถูกต้อง หมดอายุ หรือถูกใช้แล้ว")
    if action_token.action not in allowed_actions:
        raise AppointmentError("ลิงก์นี้ไม่รองรับการดำเนินการดังกล่าว")
    appointment = db.get(Appointment, action_token.appointment_id)
    revision = db.get(AppointmentRevision, action_token.revision_id)
    if not appointment or not revision or appointment.current_revision_id != revision.id:
        raise AppointmentError("ข้อเสนอนี้ไม่ใช่ revision ปัจจุบัน")
    mapping = db.scalar(
        select(LineGroupMapping).where(
            LineGroupMapping.line_group_id == line_group_id,
            LineGroupMapping.hospital_id == appointment.hospital_id,
            LineGroupMapping.group_type == "HOSPITAL",
            bool_filter(LineGroupMapping.active, True),
        )
    )
    if not mapping:
        raise AppointmentError("LINE group ไม่มีสิทธิ์ตอบรับนัดนี้")
    return action_token, appointment, revision


def confirm_appointment(db: Session, token: str, line_group_id: str) -> Appointment:
    action_token, appointment, revision = _validate_action_token(
        db, token, line_group_id, {"CONFIRM_OR_RESCHEDULE"}
    )
    if appointment.status not in {AppointmentStatus.PENDING_CONFIRMATION, AppointmentStatus.RESCHEDULE_REQUESTED}:
        raise AppointmentError("สถานะนัดไม่รองรับการยืนยัน")
    appointment.status = AppointmentStatus.CONFIRMED
    appointment.confirmed_revision_id = revision.id
    appointment.confirmed_at = datetime.now(UTC)
    appointment.confirmation_source = "LINE_HOSPITAL_GROUP"
    action_token.used_at = datetime.now(UTC)
    record_audit(
        db, actor=None, actor_label=line_group_id, action="HOSPITAL_CONFIRMED",
        entity_type="appointment", entity_id=appointment.id,
        new_values={"confirmed_revision_id": str(revision.id)}, source="LINE", revision_number=revision.revision_number,
    )
    return appointment


def request_reschedule(
    db: Session,
    token: str,
    line_group_id: str,
    preferred_date: date | None,
    message: str | None,
) -> Appointment:
    action_token, appointment, revision = _validate_action_token(
        db,
        token,
        line_group_id,
        {"CONFIRM_OR_RESCHEDULE", "RESCHEDULE_ONLY"},
    )
    appointment.status = AppointmentStatus.RESCHEDULE_REQUESTED
    action_token.used_at = datetime.now(UTC)
    db.add(RescheduleRequest(
        appointment_id=appointment.id,
        revision_id=revision.id,
        preferred_date=preferred_date,
        message=message,
        source_group_id=line_group_id,
    ))
    record_audit(
        db, actor=None, actor_label=line_group_id, action="HOSPITAL_RESCHEDULE_REQUESTED",
        entity_type="appointment", entity_id=appointment.id,
        new_values={"preferred_date": preferred_date.isoformat() if preferred_date else None, "message": message},
        source="LINE", revision_number=revision.revision_number,
    )
    return appointment


def technician_date_change(
    db: Session, appointment_id: uuid.UUID, request: DateChangeRequest, admin: User
) -> AppointmentRevision:
    appointment = db.scalar(lock_query(select(Appointment).where(Appointment.id == appointment_id), Appointment, db))
    if not appointment:
        raise AppointmentError("ไม่พบนัดหมาย")
    if appointment.version != request.expected_appointment_version:
        raise AppointmentError("นัดหมายถูกแก้ไขแล้ว กรุณาโหลดข้อมูลใหม่")
    if appointment.status != AppointmentStatus.CONFIRMED or not appointment.confirmed_revision_id:
        raise AppointmentError("ขั้นตอนนี้ใช้กับนัดที่โรงพยาบาลเคยยืนยันแล้ว")
    current = db.get(AppointmentRevision, appointment.current_revision_id)
    if not current:
        raise AppointmentError("ไม่พบ revision ปัจจุบัน")
    if current.scheduled_date == request.scheduled_date:
        raise AppointmentError("วันใหม่ต้องต่างจากวันปัจจุบัน")
    revision_number = db.scalar(
        select(func.max(AppointmentRevision.revision_number)).where(
            AppointmentRevision.appointment_id == appointment.id
        )
    ) or 0
    revision = AppointmentRevision(
        appointment_id=appointment.id,
        revision_number=revision_number + 1,
        scheduled_date=request.scheduled_date,
        service_type=current.service_type,
        notes=current.notes,
        change_source=ChangeSource.TECHNICIAN,
        requested_by=request.requested_by,
        approved_by_id=admin.id,
        reason=request.reason,
    )
    db.add(revision)
    db.flush()
    appointment.current_revision_id = revision.id
    mapping = db.scalar(
        select(LineGroupMapping).where(
            LineGroupMapping.hospital_id == appointment.hospital_id,
            LineGroupMapping.group_type == "HOSPITAL",
            bool_filter(LineGroupMapping.active, True),
        )
    )
    if not mapping:
        raise AppointmentError("ไม่พบ LINE group สำหรับแจ้งวันนัดใหม่")
    raw_token = secrets.token_urlsafe(32)
    db.add(ActionToken(
        token_hash=_hash_token(raw_token),
        appointment_id=appointment.id,
        revision_id=revision.id,
        action="RESCHEDULE_ONLY",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    ))
    _queue_notification(
        db, kind="TECHNICIAN_DATE_CHANGE", destination_id=mapping.line_group_id,
        appointment=appointment, revision=revision, action_token=raw_token,
    )
    record_audit(
        db, actor=admin, action="TECHNICIAN_DATE_CHANGE_APPROVED", entity_type="appointment",
        entity_id=appointment.id,
        old_values={"date": current.scheduled_date.isoformat(), "confirmed_revision_id": str(appointment.confirmed_revision_id)},
        new_values={"date": revision.scheduled_date.isoformat(), "current_revision_id": str(revision.id)},
        reason=request.reason, revision_number=revision.revision_number,
    )
    return revision

