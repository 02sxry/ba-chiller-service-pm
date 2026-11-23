from app.domain.enums import DraftStatus, Role
from app.domain.models import Hospital, User
from app.services.drafts import approve_hospital_as_new, match_hospital_draft, prepare_hospital_draft


def test_unknown_hospital_creates_reviewable_draft(db) -> None:
    hospital, draft = prepare_hospital_draft(db, "โรงพยาบาลใหม่ที่ยังไม่มี")
    assert hospital is None
    assert draft is not None
    assert draft.status == DraftStatus.PENDING
    assert draft.proposed_data["hospital_name"] == "โรงพยาบาลใหม่ที่ยังไม่มี"


def test_draft_can_be_approved_as_new_hospital(db) -> None:
    admin = User(email="draft-admin@example.com", password_hash="x", display_name="Admin", role=Role.ADMIN)
    db.add(admin)
    db.flush()
    _, draft = prepare_hospital_draft(db, "รพ. ใหม่")
    hospital = approve_hospital_as_new(db, draft.id, "NEW-001", "โรงพยาบาลใหม่", admin)
    db.flush()
    assert draft.status == DraftStatus.APPROVED
    assert draft.resolved_record_id == hospital.id


def test_draft_match_can_add_alias(db) -> None:
    admin = User(email="alias-admin@example.com", password_hash="x", display_name="Admin", role=Role.ADMIN)
    hospital = Hospital(hospital_code="ALIAS-001", hospital_name="โรงพยาบาลกลาง")
    db.add_all([admin, hospital])
    db.flush()
    _, draft = prepare_hospital_draft(db, "ศูนย์แพทย์กลาง", confidence_threshold=100)
    matched = match_hospital_draft(db, draft.id, hospital.id, admin, add_alias=True)
    db.flush()
    assert matched.id == hospital.id
    assert draft.status == DraftStatus.MATCHED
    assert hospital.aliases[0].alias == "ศูนย์แพทย์กลาง"

