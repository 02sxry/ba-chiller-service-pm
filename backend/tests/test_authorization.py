import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select, true

from app.core.db import get_db
from app.core.security import create_access_token
from app.domain.enums import AppointmentStatus, PlanningMode, Role
from app.domain.models import AnnualPlan, Appointment, AuditLog, Hospital, NextYearPlanDraft, PMSlot, User
from app.main import app


def make_user(db, email: str, role: Role) -> User:
    user = User(username=email.partition("@")[0], email=email, password_hash="unused", display_name=email, role=role)
    db.add(user)
    db.flush()
    return user


def client_for(db) -> TestClient:
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app, raise_server_exceptions=True)


def test_anonymous_request_is_denied(db) -> None:
    client = client_for(db)
    try:
        response = client.get("/api/v1/hospitals")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_viewer_can_read_but_cannot_create_hospital(db) -> None:
    viewer = make_user(db, "viewer-auth@example.com", Role.VIEWER)
    client = client_for(db)
    headers = {"Authorization": f"Bearer {create_access_token(viewer)}"}
    try:
        assert client.get("/api/v1/hospitals", headers=headers).status_code == 200
        response = client.post(
            "/api/v1/hospitals",
            headers=headers,
            json={"hospital_code": "AUTH-H1", "hospital_name": "โรงพยาบาลไม่มีสิทธิ์"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_admin_can_create_hospital(db) -> None:
    admin = make_user(db, "admin-auth@example.com", Role.ADMIN)
    client = client_for(db)
    headers = {"Authorization": f"Bearer {create_access_token(admin)}"}
    try:
        response = client.post(
            "/api/v1/hospitals",
            headers=headers,
            json={"hospital_code": "", "hospital_name": "โรงพยาบาลมีสิทธิ์"},
        )
        assert response.status_code == 201
        hospital = response.json()
        assert hospital["hospital_code"].startswith("HOSP-")
        assert hospital["hospital_name"] == "โรงพยาบาลมีสิทธิ์"
        event = db.scalar(select(AuditLog).where(AuditLog.entity_id == uuid.UUID(hospital["id"])))
        assert event.new_values["hospital_name"] == hospital["hospital_name"]
    finally:
        app.dependency_overrides.clear()


def test_admin_can_create_multiple_hospitals_in_sequence(db) -> None:
    admin = make_user(db, "admin-multiple-hospitals@example.com", Role.ADMIN)
    client = client_for(db)
    headers = {"Authorization": f"Bearer {create_access_token(admin)}"}
    try:
        first = client.post(
            "/api/v1/hospitals",
            headers=headers,
            json={"hospital_name": " โรงพยาบาลลำดับหนึ่ง "},
        )
        second = client.post(
            "/api/v1/hospitals",
            headers=headers,
            json={"hospital_name": "โรงพยาบาลลำดับสอง"},
        )

        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["hospital_name"] == "โรงพยาบาลลำดับหนึ่ง"
        assert second.json()["hospital_name"] == "โรงพยาบาลลำดับสอง"
        assert first.json()["hospital_code"] != second.json()["hospital_code"]
    finally:
        app.dependency_overrides.clear()


def test_admin_me_accepts_internal_legacy_email(db) -> None:
    admin = User(
        username="admin",
        email="admin@local.invalid",
        password_hash="unused",
        display_name="Admin",
        role=Role.ADMIN,
    )
    db.add(admin)
    db.flush()
    client = client_for(db)
    headers = {"Authorization": f"Bearer {create_access_token(admin)}"}
    try:
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["username"] == "admin"
    finally:
        app.dependency_overrides.clear()


def test_admin_can_delete_unused_user_permanently(db) -> None:
    admin = make_user(db, "admin-delete@example.com", Role.ADMIN)
    target = make_user(db, "delete-me@example.com", Role.VIEWER)
    client = client_for(db)
    headers = {"Authorization": f"Bearer {create_access_token(admin)}"}
    try:
        response = client.delete(f"/api/v1/users/{target.id}/permanent", headers=headers)
        assert response.status_code == 200
        assert response.json()["email"] == "delete-me@example.com"
        assert client.get("/api/v1/users", headers=headers).json()
    finally:
        app.dependency_overrides.clear()


def test_equipment_archive_then_permanent_delete(db) -> None:
    admin = make_user(db, "admin-equipment@example.com", Role.ADMIN)
    hospital = Hospital(hospital_code="ARCH-H1", hospital_name="โรงพยาบาล Archive")
    db.add(hospital)
    db.flush()
    client = client_for(db)
    headers = {"Authorization": f"Bearer {create_access_token(admin)}"}
    try:
        created = client.post(
            "/api/v1/equipment",
            headers=headers,
            json={"hospital_id": str(hospital.id), "equipment_code": "ARCH-E1", "equipment_name": "เครื่อง Archive"},
        )
        assert created.status_code == 201
        equipment_id = created.json()["id"]
        archived = client.delete(f"/api/v1/equipment/{equipment_id}", headers=headers)
        assert archived.status_code == 200
        archive_list = client.get("/api/v1/equipment/archive", headers=headers)
        assert archive_list.status_code == 200
        assert archive_list.json()[0]["equipment_name"] == "เครื่อง Archive"
        deleted = client.delete(f"/api/v1/equipment/{equipment_id}/permanent", headers=headers)
        assert deleted.status_code == 200
        assert client.get("/api/v1/equipment/archive", headers=headers).json() == []
    finally:
        app.dependency_overrides.clear()


def test_archiving_equipment_closes_linked_pm_data(db) -> None:
    admin = make_user(db, "admin-cascade@example.com", Role.ADMIN)
    hospital = Hospital(hospital_code="CAS-H1", hospital_name="โรงพยาบาล Cascade")
    db.add(hospital)
    db.flush()
    client = client_for(db)
    headers = {"Authorization": f"Bearer {create_access_token(admin)}"}
    try:
        created = client.post(
            "/api/v1/equipment",
            headers=headers,
            json={"hospital_id": str(hospital.id), "equipment_code": "CAS-E1", "equipment_name": "เครื่อง Cascade"},
        )
        assert created.status_code == 201
        equipment_id = uuid.UUID(created.json()["id"])

        plan_response = client.post(
            "/api/v1/plans/approve",
            headers=headers,
            json={
                "equipment_id": str(equipment_id),
                "plan_year": 2035,
                "annual_frequency": 2,
                "planning_mode": PlanningMode.AUTOMATIC.value,
                "start_month": 1,
            },
        )
        assert plan_response.status_code == 201
        plan_id = uuid.UUID(plan_response.json()["id"])
        slot = db.scalar(select(PMSlot).where(PMSlot.yearly_plan_id == plan_id))
        assert slot is not None
        db.add(Appointment(
            pm_slot_id=slot.id,
            hospital_id=hospital.id,
            equipment_id=equipment_id,
            status=AppointmentStatus.PENDING_CONFIRMATION,
        ))
        db.flush()

        draft_response = client.post(
            "/api/v1/next-year-drafts/generate?source_year=2035&target_year=2036",
            headers=headers,
        )
        assert draft_response.status_code == 200

        archived = client.delete(f"/api/v1/equipment/{equipment_id}", headers=headers)
        assert archived.status_code == 200
        db.expire_all()

        plan = db.get(AnnualPlan, plan_id)
        assert plan is not None and plan.active is False
        assert db.scalars(
            select(PMSlot).where(PMSlot.equipment_id == equipment_id, PMSlot.active == true())
        ).all() == []
        draft = db.scalar(select(NextYearPlanDraft).where(NextYearPlanDraft.equipment_id == equipment_id))
        assert draft is not None and draft.excluded is True
        appointment = db.scalar(select(Appointment).where(Appointment.equipment_id == equipment_id))
        assert appointment is not None and appointment.status == AppointmentStatus.CANCELLED
        assert client.get("/api/v1/slots?plan_year=2035", headers=headers).json() == []
    finally:
        app.dependency_overrides.clear()


def test_archived_equipment_with_closed_plan_can_be_deleted_permanently(db) -> None:
    admin = make_user(db, "admin-delete-equipment@example.com", Role.ADMIN)
    hospital = Hospital(hospital_code="DEL-H1", hospital_name="โรงพยาบาล Delete")
    db.add(hospital)
    db.flush()
    client = client_for(db)
    headers = {"Authorization": f"Bearer {create_access_token(admin)}"}
    try:
        created = client.post(
            "/api/v1/equipment",
            headers=headers,
            json={
                "hospital_id": str(hospital.id),
                "equipment_code": "DEL-E1",
                "equipment_name": "Chiller",
                "model": "5445435435",
                "serial_number": "001",
            },
        )
        assert created.status_code == 201
        assert created.json()["serial_number"] == "001-CH"
        equipment_id = created.json()["id"]
        plan_response = client.post(
            "/api/v1/plans/approve",
            headers=headers,
            json={
                "equipment_id": equipment_id,
                "plan_year": 2037,
                "annual_frequency": 1,
                "planning_mode": PlanningMode.AUTOMATIC.value,
                "start_month": 1,
            },
        )
        assert plan_response.status_code == 201
        assert client.delete(f"/api/v1/equipment/{equipment_id}", headers=headers).status_code == 200
        deleted = client.delete(f"/api/v1/equipment/{equipment_id}/permanent", headers=headers)
        assert deleted.status_code == 200
        assert all(item["id"] != equipment_id for item in client.get("/api/v1/equipment/archive", headers=headers).json())
    finally:
        app.dependency_overrides.clear()
