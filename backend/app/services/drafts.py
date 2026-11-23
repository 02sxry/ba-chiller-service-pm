import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import DraftStatus, DraftType
from app.domain.models import Hospital, HospitalAlias, MasterDataDraft, User
from app.services.audit import record_audit
from app.services.matching import match_hospitals, normalize_name


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

