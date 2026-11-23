from datetime import date

import pytest
from sqlalchemy import select

from app.domain.enums import AppointmentStatus, ChangeSource, PlanningMode, Role
from app.domain.models import (
    ActionToken,
    AnnualPlan,
    Equipment,
    Hospital,
    LineGroupMapping,
    NotificationJob,
    PMSlot,
    User,
)
from app.domain.schemas import AppointmentApproveRequest, DateChangeRequest
from app.services.appointments import AppointmentError, approve_appointment, confirm_appointment, technician_date_change


def seed(db):
    admin = User(email="workflow@example.com", password_hash="x", display_name="Admin", role=Role.ADMIN)
    hospital = Hospital(hospital_code="WF-H", hospital_name="โรงพยาบาล Workflow")
    equipment = Equipment(equipment_code="WF-E", hospital=hospital, equipment_name="Chiller Workflow")
    db.add_all([admin, hospital, equipment])
    db.flush()
    plan = AnnualPlan(
        equipment_id=equipment.id,
        plan_year=2027,
        annual_frequency=1,
        planning_mode=PlanningMode.AUTOMATIC,
        start_month=1,
        planned_months=[1],
        approved_by_id=admin.id,
    )
    slot = PMSlot(plan=plan, equipment_id=equipment.id, plan_year=2027, planned_month=1)
    mapping = LineGroupMapping(line_group_id="hospital-group", group_type="HOSPITAL", hospital_id=hospital.id)
    db.add_all([plan, slot, mapping])
    db.flush()
    return admin, hospital, equipment, slot


def test_confirmation_and_technician_change_preserve_original_confirmation(db) -> None:
    admin, hospital, equipment, slot = seed(db)
    appointment, token = approve_appointment(
        db,
        AppointmentApproveRequest(
            pm_slot_id=slot.id,
            scheduled_date=date(2027, 1, 15),
            hospital_id=hospital.id,
            equipment_id=equipment.id,
            service_type="PM",
            expected_slot_version=slot.version,
        ),
        admin,
    )
    db.flush()
    original_revision_id = appointment.current_revision_id
    confirmed = confirm_appointment(db, token, "hospital-group")
    db.flush()
    assert confirmed.status == AppointmentStatus.CONFIRMED
    assert confirmed.confirmed_revision_id == original_revision_id

    changed = technician_date_change(
        db,
        appointment.id,
        DateChangeRequest(
            scheduled_date=date(2027, 1, 20),
            expected_appointment_version=appointment.version,
            reason="ช่างติดภารกิจ",
            requested_by="ช่างหนึ่ง",
        ),
        admin,
    )
    db.flush()
    assert changed.revision_number == 2
    assert changed.change_source == ChangeSource.TECHNICIAN
    assert appointment.current_revision_id == changed.id
    assert appointment.confirmed_revision_id == original_revision_id
    assert appointment.status == AppointmentStatus.CONFIRMED
    assert appointment.pm_slot_id == slot.id
    action_token = db.scalar(select(ActionToken).where(ActionToken.revision_id == changed.id))
    notification = db.scalar(select(NotificationJob).where(NotificationJob.revision_id == changed.id))
    assert action_token.action == "RESCHEDULE_ONLY"
    assert notification.payload["actions"]["reschedule"].startswith("action=reschedule&token=")


def test_duplicate_active_appointment_is_rejected(db) -> None:
    admin, hospital, equipment, slot = seed(db)
    request = AppointmentApproveRequest(
        pm_slot_id=slot.id,
        scheduled_date=date(2027, 1, 15),
        hospital_id=hospital.id,
        equipment_id=equipment.id,
        service_type="PM",
        expected_slot_version=slot.version,
    )
    approve_appointment(db, request, admin)
    db.flush()
    with pytest.raises(AppointmentError, match="มีนัดอยู่แล้ว"):
        approve_appointment(db, request, admin)


def test_models_have_no_completed_status() -> None:
    assert "COMPLETED" not in {status.value for status in AppointmentStatus}

