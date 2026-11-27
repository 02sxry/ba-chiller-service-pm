import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import create_access_token
from app.domain.enums import PlanningMode, Role
from app.domain.models import AnnualPlan, Equipment, Hospital, LineGroupMapping, NotificationJob, PMSlot, User
from app.main import app


def test_signed_technician_intake_can_be_approved_once(db, monkeypatch) -> None:
    secret = "test-line-channel-secret"
    monkeypatch.setattr(get_settings(), "line_channel_secret", secret)
    admin = User(username="uat", email="uat@local.dev", password_hash="unused", display_name="ผู้ตรวจสอบ", role=Role.ADMIN)
    hospital = Hospital(hospital_code="INTAKE-H1", hospital_name="โรงพยาบาลขอนแก่น")
    equipment = Equipment(equipment_code="INTAKE-E1", hospital=hospital, equipment_name="Xstrahl", room_location="ตึก 72 ปี")
    db.add_all([admin, hospital, equipment])
    db.flush()
    plan = AnnualPlan(
        equipment_id=equipment.id, plan_year=2026, annual_frequency=1, planning_mode=PlanningMode.AUTOMATIC,
        start_month=12, planned_months=[12], approved_by_id=admin.id,
    )
    slot = PMSlot(plan=plan, equipment_id=equipment.id, plan_year=2026, planned_month=12)
    db.add_all([
        slot, LineGroupMapping(line_group_id="uat-tech", group_type="TECHNICIAN"),
        LineGroupMapping(line_group_id="uat-hospital", group_type="HOSPITAL", hospital_id=hospital.id),
    ])
    db.flush()

    def override_db():
        yield db

    raw_text = "ขอนแก่นXstrahl 19/12/69"
    body = json.dumps({"events": [{
        "webhookEventId": "uat-tech-event", "type": "message",
        "timestamp": int(datetime(2026, 11, 27, tzinfo=UTC).timestamp() * 1000),
        "source": {"type": "group", "groupId": "uat-tech"},
        "message": {"type": "text", "text": raw_text},
    }]}, ensure_ascii=False).encode()
    signature = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    webhook_headers = {"X-Line-Signature": signature, "Content-Type": "application/json"}
    headers = {"Authorization": f"Bearer {create_access_token(admin)}"}
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            webhook = client.post("/api/v1/line/webhook", headers=webhook_headers, content=body)
            assert webhook.json()["actions"][0]["result"] == "TECHNICIAN_INTAKE_PARSED"
            assert client.post("/api/v1/line/webhook", headers=webhook_headers, content=body).json()["accepted_events"] == 0
            intake, = client.get("/api/v1/intakes", headers=headers).json()
            assert intake["raw_text"] == raw_text
            assert intake["parsed_data"]["proposed_date"] == "2026-12-19"
            assert db.scalar(select(NotificationJob).where(NotificationJob.kind == "APPOINTMENT_PROPOSAL")) is None
            approval_path = f"/api/v1/intakes/{intake['id']}/items/0/approve"
            approval_input = {
                "pm_slot_id": str(slot.id), "scheduled_date": "2026-12-19",
                "hospital_id": str(hospital.id), "equipment_id": str(equipment.id),
                "expected_slot_version": slot.version,
            }
            approved = client.post(approval_path, headers=headers, json=approval_input)
            assert approved.status_code == 201, approved.text
            assert approved.json()["status"] == "PENDING_CONFIRMATION"
            assert client.post(approval_path, headers=headers, json=approval_input).status_code == 409
            assert client.get("/api/v1/intakes", headers=headers).json()[0]["state"] == "CONVERTED_TO_APPOINTMENT"
            calendar, = client.get("/api/v1/appointments", headers=headers).json()
            assert calendar["hospital_name"] == hospital.hospital_name
            assert calendar["scheduled_date"] == "2026-12-19"
            notification = db.scalar(select(NotificationJob).where(NotificationJob.kind == "APPOINTMENT_PROPOSAL"))
            assert notification.destination_id == "uat-hospital"
            assert notification.payload["room_location"] == "ตึก 72 ปี"
    finally:
        app.dependency_overrides.clear()
