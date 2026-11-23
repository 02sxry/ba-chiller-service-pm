from datetime import date

import pytest

from app.domain.enums import DraftStatus, PlanningMode, Role
from app.domain.models import Hospital, User
from app.services.drafts import (
    DraftError,
    approve_equipment_draft,
    approve_hospital_as_new,
    approve_plan_draft,
    match_hospital_draft,
    prepare_equipment_draft,
    prepare_hospital_draft,
    prepare_plan_draft,
)


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


def test_dependent_drafts_require_parent_approval(db) -> None:
    admin = User(email="dependency-admin@example.com", password_hash="x", display_name="Admin", role=Role.ADMIN)
    db.add(admin)
    db.flush()
    _, hospital_draft = prepare_hospital_draft(db, "โรงพยาบาลสายสัมพันธ์")
    _, equipment_draft = prepare_equipment_draft(
        db,
        "Chiller สายสัมพันธ์ 1",
        hospital_draft_id=hospital_draft.id,
    )
    plan_draft = prepare_plan_draft(
        db,
        date(2027, 4, 18),
        equipment_draft_id=equipment_draft.id,
    )
    assert equipment_draft.parent_draft_id == hospital_draft.id
    assert plan_draft.parent_draft_id == equipment_draft.id
    assert plan_draft.proposed_data["annual_frequency"] is None
    assert plan_draft.proposed_data["planned_months"] == []
    with pytest.raises(DraftError, match="Hospital Draft ก่อน"):
        approve_equipment_draft(
            db,
            equipment_draft.id,
            equipment_code="DEP-E001",
            equipment_name="Chiller สายสัมพันธ์ 1",
            admin=admin,
        )
    with pytest.raises(DraftError, match="Equipment Draft ก่อน"):
        approve_plan_draft(
            db,
            plan_draft.id,
            annual_frequency=4,
            planning_mode=PlanningMode.AUTOMATIC,
            start_month=1,
            planned_months=None,
            admin=admin,
        )


def test_dependent_drafts_approve_in_order(db) -> None:
    admin = User(email="chain-admin@example.com", password_hash="x", display_name="Admin", role=Role.ADMIN)
    db.add(admin)
    db.flush()
    _, hospital_draft = prepare_hospital_draft(db, "โรงพยาบาลลูกโซ่")
    _, equipment_draft = prepare_equipment_draft(
        db,
        "Chiller ลูกโซ่ 1",
        hospital_draft_id=hospital_draft.id,
    )
    plan_draft = prepare_plan_draft(
        db,
        date(2027, 4, 18),
        equipment_draft_id=equipment_draft.id,
    )
    hospital = approve_hospital_as_new(
        db,
        hospital_draft.id,
        "CHAIN-H001",
        "โรงพยาบาลลูกโซ่",
        admin,
    )
    equipment = approve_equipment_draft(
        db,
        equipment_draft.id,
        equipment_code="CHAIN-E001",
        equipment_name="Chiller ลูกโซ่ 1",
        admin=admin,
    )
    plan = approve_plan_draft(
        db,
        plan_draft.id,
        annual_frequency=4,
        planning_mode=PlanningMode.AUTOMATIC,
        start_month=1,
        planned_months=None,
        admin=admin,
    )
    db.flush()
    assert equipment.hospital_id == hospital.id
    assert plan.equipment_id == equipment.id
    assert plan.planned_months == [1, 4, 7, 10]
    assert len(plan.slots) == 4
    assert hospital_draft.status == DraftStatus.APPROVED
    assert equipment_draft.status == DraftStatus.APPROVED
    assert plan_draft.status == DraftStatus.APPROVED

