import uuid

import pytest

from app.domain.enums import PlanningMode, Role
from app.domain.models import Equipment, Hospital, User
from app.domain.schemas import PlanApproveRequest, PlanPreviewRequest
from app.services.planning import PlanningError, approve_plan, calculate_months, calculate_periods


@pytest.mark.parametrize(
    ("frequency", "start", "expected"),
    [
        (1, 8, [8]),
        (2, 1, [1, 7]),
        (3, 2, [2, 6, 10]),
        (4, 1, [1, 4, 7, 10]),
        (4, 10, [10, 1, 4, 7]),
        (6, 2, [2, 4, 6, 8, 10, 12]),
        (12, 1, list(range(1, 13))),
    ],
)
def test_automatic_months(frequency: int, start: int, expected: list[int]) -> None:
    request = PlanPreviewRequest(
        plan_year=2027,
        annual_frequency=frequency,
        planning_mode=PlanningMode.AUTOMATIC,
        start_month=start,
    )
    assert calculate_months(request) == expected


def test_automatic_periods_continue_into_next_year() -> None:
    request = PlanPreviewRequest(
        plan_year=2027,
        annual_frequency=4,
        planning_mode=PlanningMode.AUTOMATIC,
        start_month=10,
    )
    assert calculate_periods(request) == [(2027, 10), (2028, 1), (2028, 4), (2028, 7)]


def test_manual_months_reject_duplicates() -> None:
    request = PlanPreviewRequest(
        plan_year=2027,
        annual_frequency=3,
        planning_mode=PlanningMode.MANUAL,
        planned_months=[1, 1, 7],
    )
    with pytest.raises(PlanningError, match="ต้องไม่ซ้ำ"):
        calculate_months(request)


def test_approve_plan_creates_slots_atomically(db) -> None:
    admin = User(
        id=uuid.uuid4(), email="admin@example.com", password_hash="x", display_name="Admin", role=Role.ADMIN
    )
    hospital = Hospital(hospital_code="H001", hospital_name="โรงพยาบาลทดสอบ")
    equipment = Equipment(
        equipment_code="E001", hospital=hospital, equipment_name="Chiller 1"
    )
    db.add_all([admin, hospital, equipment])
    db.flush()
    request = PlanApproveRequest(
        equipment_id=equipment.id,
        plan_year=2027,
        annual_frequency=4,
        planning_mode=PlanningMode.AUTOMATIC,
        start_month=10,
    )
    plan = approve_plan(db, request, admin)
    db.flush()
    assert plan.planned_months == [10, 1, 4, 7]
    assert [(slot.plan_year, slot.planned_month) for slot in plan.slots] == [
        (2027, 10),
        (2028, 1),
        (2028, 4),
        (2028, 7),
    ]
    assert all(slot.equipment_id == equipment.id for slot in plan.slots)


def test_inactive_hospital_cannot_receive_new_plan() -> None:
    admin = User(
        email="admin-inactive-hospital@example.com",
        password_hash="x",
        display_name="Admin",
        role=Role.ADMIN,
    )
    hospital = Hospital(
        id=uuid.uuid4(),
        hospital_code="H-INACTIVE",
        hospital_name="โรงพยาบาลปิด",
        active=False,
    )
    equipment = Equipment(
        id=uuid.uuid4(),
        equipment_code="E-INACTIVE",
        hospital_id=hospital.id,
        equipment_name="Chiller",
        active=True,
    )

    class FakeSession:
        def get(self, model, record_id):
            if model is Equipment and record_id == equipment.id:
                return equipment
            if model is Hospital and record_id == hospital.id:
                return hospital
            return None

    request = PlanApproveRequest(
        equipment_id=equipment.id,
        plan_year=2027,
        annual_frequency=4,
        planning_mode=PlanningMode.AUTOMATIC,
        start_month=10,
    )
    with pytest.raises(PlanningError, match="โรงพยาบาลของอุปกรณ์นี้ปิดใช้งานแล้ว"):
        approve_plan(FakeSession(), request, admin)


def test_database_rejects_duplicate_yearly_plan(db) -> None:
    admin = User(
        email="admin2@example.com", password_hash="x", display_name="Admin", role=Role.ADMIN
    )
    hospital = Hospital(hospital_code="H002", hospital_name="โรงพยาบาลสอง")
    equipment = Equipment(equipment_code="E002", hospital=hospital, equipment_name="Chiller 2")
    db.add_all([admin, hospital, equipment])
    db.flush()
    request = PlanApproveRequest(
        equipment_id=equipment.id,
        plan_year=2027,
        annual_frequency=1,
        planning_mode=PlanningMode.AUTOMATIC,
        start_month=1,
    )
    approve_plan(db, request, admin)
    db.flush()
    with pytest.raises(PlanningError, match="มีแผนรายปี"):
        approve_plan(db, request, admin)

