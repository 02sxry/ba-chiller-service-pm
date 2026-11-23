import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import DraftStatus, DraftType, PlanningMode
from app.domain.models import Equipment, Hospital, HospitalAlias, MasterDataDraft, User
from app.domain.schemas import PlanApproveRequest
from app.services.audit import record_audit
from app.services.matching import match_equipment, match_hospitals, normalize_name
from app.services.planning import approve_plan


class DraftError(ValueError):
    pass


def prepare_hospital_draft(
    db: Session,
    original_text: str,
    *,
    confidence_threshold: int = 90,
) -> tuple[Hospital | None, MasterDataDraft | None]:
    matches = match_hospitals(db, original_text)
    if matches and matches[0].score >= confidence_threshold:
        return db.get(Hospital, matches[0].record_id), None
    existing = db.scalar(
        select(MasterDataDraft).where(
            MasterDataDraft.draft_type == DraftType.HOSPITAL,
            MasterDataDraft.status == DraftStatus.PENDING,
            MasterDataDraft.original_text == original_text,
        )
    )
    if existing:
        return None, existing
    draft = MasterDataDraft(
        draft_type=DraftType.HOSPITAL,
        original_text=original_text,
        proposed_data={"hospital_name": original_text.strip()},
        suggestions=[
            {"record_id": str(match.record_id), "label": match.label, "score": match.score}
            for match in matches
        ],
    )
    db.add(draft)
    db.flush()
    record_audit(
        db,
        actor=None,
        action="HOSPITAL_DRAFT_CREATED",
        entity_type="master_data_draft",
        entity_id=draft.id,
        new_values={"original_text": original_text, "suggestions": draft.suggestions},
        source="INTAKE",
    )
    return None, draft


def approve_hospital_as_new(
    db: Session,
    draft_id: uuid.UUID,
    hospital_code: str,
    hospital_name: str,
    admin: User,
) -> Hospital:
    draft = db.scalar(select(MasterDataDraft).where(MasterDataDraft.id == draft_id).with_for_update())
    if not draft or draft.draft_type != DraftType.HOSPITAL:
        raise DraftError("ไม่พบ Hospital Draft")
    if draft.status != DraftStatus.PENDING:
        raise DraftError("Draft นี้ผ่านการพิจารณาแล้ว")
    hospital = Hospital(hospital_code=hospital_code, hospital_name=hospital_name)
    db.add(hospital)
    db.flush()
    draft.status = DraftStatus.APPROVED
    draft.resolved_record_id = hospital.id
    draft.reviewed_by_id = admin.id
    draft.reviewed_at = datetime.now(UTC)
    record_audit(
        db,
        actor=admin,
        action="HOSPITAL_DRAFT_APPROVED_NEW",
        entity_type="hospital",
        entity_id=hospital.id,
        new_values={"hospital_code": hospital_code, "hospital_name": hospital_name},
    )
    return hospital


def match_hospital_draft(
    db: Session,
    draft_id: uuid.UUID,
    hospital_id: uuid.UUID,
    admin: User,
    *,
    add_alias: bool,
) -> Hospital:
    draft = db.scalar(select(MasterDataDraft).where(MasterDataDraft.id == draft_id).with_for_update())
    hospital = db.get(Hospital, hospital_id)
    if not draft or draft.draft_type != DraftType.HOSPITAL or not hospital:
        raise DraftError("ไม่พบ Draft หรือโรงพยาบาล")
    if draft.status != DraftStatus.PENDING:
        raise DraftError("Draft นี้ผ่านการพิจารณาแล้ว")
    if add_alias:
        normalized = normalize_name(draft.original_text)
        conflict = db.scalar(select(HospitalAlias).where(HospitalAlias.normalized_alias == normalized))
        if conflict and conflict.hospital_id != hospital.id:
            raise DraftError("Alias นี้ผูกกับโรงพยาบาลอื่นแล้ว")
        if not conflict:
            db.add(HospitalAlias(hospital=hospital, alias=draft.original_text, normalized_alias=normalized))
    draft.status = DraftStatus.MATCHED
    draft.resolved_record_id = hospital.id
    draft.reviewed_by_id = admin.id
    draft.reviewed_at = datetime.now(UTC)
    record_audit(
        db,
        actor=admin,
        action="HOSPITAL_DRAFT_MATCHED",
        entity_type="master_data_draft",
        entity_id=draft.id,
        new_values={"hospital_id": str(hospital.id), "alias_added": add_alias},
    )
    return hospital


def prepare_equipment_draft(
    db: Session,
    original_text: str,
    *,
    hospital_id: uuid.UUID | None = None,
    hospital_draft_id: uuid.UUID | None = None,
    confidence_threshold: int = 90,
) -> tuple[Equipment | None, MasterDataDraft | None]:
    if bool(hospital_id) == bool(hospital_draft_id):
        raise DraftError("ต้องระบุ hospital_id หรือ hospital_draft_id อย่างใดอย่างหนึ่ง")
    if hospital_id:
        hospital = db.get(Hospital, hospital_id)
        if not hospital:
            raise DraftError("ไม่พบโรงพยาบาล")
        matches = match_equipment(db, hospital_id, original_text)
        if matches and matches[0].score >= confidence_threshold:
            return db.get(Equipment, matches[0].record_id), None
    else:
        hospital_draft = db.get(MasterDataDraft, hospital_draft_id)
        if not hospital_draft or hospital_draft.draft_type != DraftType.HOSPITAL:
            raise DraftError("ไม่พบ Hospital Draft ที่เป็น dependency")
        matches = []
    duplicate_conditions = [
        MasterDataDraft.draft_type == DraftType.EQUIPMENT,
        MasterDataDraft.status == DraftStatus.PENDING,
        MasterDataDraft.original_text == original_text,
        MasterDataDraft.parent_draft_id == hospital_draft_id,
    ]
    if hospital_id:
        duplicate_conditions.append(
            MasterDataDraft.proposed_data["hospital_id"].as_string() == str(hospital_id)
        )
    existing = db.scalar(select(MasterDataDraft).where(*duplicate_conditions))
    if existing:
        return None, existing
    draft = MasterDataDraft(
        draft_type=DraftType.EQUIPMENT,
        original_text=original_text,
        parent_draft_id=hospital_draft_id,
        proposed_data={
            "hospital_id": str(hospital_id) if hospital_id else None,
            "equipment_name": original_text.strip(),
            "manufacturer_id": None,
            "model": None,
            "serial_number": None,
            "equipment_code": None,
        },
        suggestions=[
            {"record_id": str(match.record_id), "label": match.label, "score": match.score}
            for match in matches
        ],
    )
    db.add(draft)
    db.flush()
    record_audit(
        db,
        actor=None,
        action="EQUIPMENT_DRAFT_CREATED",
        entity_type="master_data_draft",
        entity_id=draft.id,
        new_values={"original_text": original_text, "parent_draft_id": str(hospital_draft_id) if hospital_draft_id else None},
        source="INTAKE",
    )
    return None, draft


def approve_equipment_draft(
    db: Session,
    draft_id: uuid.UUID,
    *,
    equipment_code: str,
    equipment_name: str,
    admin: User,
    manufacturer_id: uuid.UUID | None = None,
    equipment_type_id: uuid.UUID | None = None,
    model: str | None = None,
    serial_number: str | None = None,
    room_location: str | None = None,
    notes: str | None = None,
) -> Equipment:
    draft = db.scalar(select(MasterDataDraft).where(MasterDataDraft.id == draft_id).with_for_update())
    if not draft or draft.draft_type != DraftType.EQUIPMENT:
        raise DraftError("ไม่พบ Equipment Draft")
    if draft.status != DraftStatus.PENDING:
        raise DraftError("Draft นี้ผ่านการพิจารณาแล้ว")
    hospital_id = draft.proposed_data.get("hospital_id")
    if draft.parent_draft_id:
        parent = db.get(MasterDataDraft, draft.parent_draft_id)
        if not parent or parent.status not in {DraftStatus.APPROVED, DraftStatus.MATCHED} or not parent.resolved_record_id:
            raise DraftError("ต้องอนุมัติ Hospital Draft ก่อน")
        hospital_id = str(parent.resolved_record_id)
    if not hospital_id or not db.get(Hospital, uuid.UUID(hospital_id)):
        raise DraftError("ไม่พบโรงพยาบาลที่อนุมัติแล้ว")
    equipment = Equipment(
        equipment_code=equipment_code,
        hospital_id=uuid.UUID(hospital_id),
        manufacturer_id=manufacturer_id,
        equipment_type_id=equipment_type_id,
        equipment_name=equipment_name,
        model=model,
        serial_number=serial_number,
        room_location=room_location,
        notes=notes,
    )
    db.add(equipment)
    db.flush()
    draft.status = DraftStatus.APPROVED
    draft.resolved_record_id = equipment.id
    draft.reviewed_by_id = admin.id
    draft.reviewed_at = datetime.now(UTC)
    record_audit(
        db,
        actor=admin,
        action="EQUIPMENT_DRAFT_APPROVED",
        entity_type="equipment",
        entity_id=equipment.id,
        new_values={"equipment_code": equipment_code, "equipment_name": equipment_name, "hospital_id": hospital_id},
    )
    return equipment


def prepare_plan_draft(
    db: Session,
    proposed_date: date,
    *,
    equipment_id: uuid.UUID | None = None,
    equipment_draft_id: uuid.UUID | None = None,
) -> MasterDataDraft:
    if bool(equipment_id) == bool(equipment_draft_id):
        raise DraftError("ต้องระบุ equipment_id หรือ equipment_draft_id อย่างใดอย่างหนึ่ง")
    if equipment_id and not db.get(Equipment, equipment_id):
        raise DraftError("ไม่พบอุปกรณ์")
    if equipment_draft_id:
        parent = db.get(MasterDataDraft, equipment_draft_id)
        if not parent or parent.draft_type != DraftType.EQUIPMENT:
            raise DraftError("ไม่พบ Equipment Draft ที่เป็น dependency")
    duplicate_conditions = [
        MasterDataDraft.draft_type == DraftType.PM_PLAN,
        MasterDataDraft.status == DraftStatus.PENDING,
        MasterDataDraft.parent_draft_id == equipment_draft_id,
        MasterDataDraft.original_text == proposed_date.isoformat(),
    ]
    if equipment_id:
        duplicate_conditions.append(
            MasterDataDraft.proposed_data["equipment_id"].as_string() == str(equipment_id)
        )
    existing = db.scalar(select(MasterDataDraft).where(*duplicate_conditions))
    if existing:
        return existing
    draft = MasterDataDraft(
        draft_type=DraftType.PM_PLAN,
        original_text=proposed_date.isoformat(),
        parent_draft_id=equipment_draft_id,
        proposed_data={
            "equipment_id": str(equipment_id) if equipment_id else None,
            "proposed_appointment_date": proposed_date.isoformat(),
            "plan_year": proposed_date.year,
            "annual_frequency": None,
            "planned_months": [],
        },
        suggestions=[],
    )
    db.add(draft)
    db.flush()
    record_audit(
        db,
        actor=None,
        action="PM_PLAN_DRAFT_CREATED",
        entity_type="master_data_draft",
        entity_id=draft.id,
        new_values=draft.proposed_data,
        source="INTAKE",
    )
    return draft


def approve_plan_draft(
    db: Session,
    draft_id: uuid.UUID,
    *,
    annual_frequency: int,
    planning_mode: PlanningMode,
    start_month: int | None,
    planned_months: list[int] | None,
    admin: User,
):
    draft = db.scalar(select(MasterDataDraft).where(MasterDataDraft.id == draft_id).with_for_update())
    if not draft or draft.draft_type != DraftType.PM_PLAN:
        raise DraftError("ไม่พบ PM Plan Draft")
    if draft.status != DraftStatus.PENDING:
        raise DraftError("Draft นี้ผ่านการพิจารณาแล้ว")
    equipment_id = draft.proposed_data.get("equipment_id")
    if draft.parent_draft_id:
        parent = db.get(MasterDataDraft, draft.parent_draft_id)
        if not parent or parent.status != DraftStatus.APPROVED or not parent.resolved_record_id:
            raise DraftError("ต้องอนุมัติ Equipment Draft ก่อน")
        equipment_id = str(parent.resolved_record_id)
    if not equipment_id:
        raise DraftError("ไม่พบอุปกรณ์ที่อนุมัติแล้ว")
    request = PlanApproveRequest(
        equipment_id=uuid.UUID(equipment_id),
        plan_year=int(draft.proposed_data["plan_year"]),
        annual_frequency=annual_frequency,
        planning_mode=planning_mode,
        start_month=start_month,
        planned_months=planned_months,
    )
    plan = approve_plan(db, request, admin)
    draft.status = DraftStatus.APPROVED
    draft.resolved_record_id = plan.id
    draft.reviewed_by_id = admin.id
    draft.reviewed_at = datetime.now(UTC)
    record_audit(
        db,
        actor=admin,
        action="PM_PLAN_DRAFT_APPROVED",
        entity_type="annual_plan",
        entity_id=plan.id,
        new_values={"frequency": annual_frequency, "months": plan.planned_months},
    )
    return plan

