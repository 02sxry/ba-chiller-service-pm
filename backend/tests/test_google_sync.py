from app.domain.enums import Role, SyncStatus
from app.domain.models import Hospital, SyncEvent, User
from app.integrations.google import GoogleResult
from app.services.google_sync import process_hospital_submission, process_outbound_event


class FailingGoogleProvider:
    def export_rows(self, worksheet, rows):
        return GoogleResult(success=False, error="quota exceeded")

    def store_file(self, folder_kind, name, content):
        return GoogleResult(success=False, error="unavailable")


def make_admin(db) -> User:
    admin = User(email="sync-admin@example.com", password_hash="x", display_name="Admin", role=Role.ADMIN)
    db.add(admin)
    db.flush()
    return admin


def test_valid_hospital_sheet_row_is_applied_once(db) -> None:
    admin = make_admin(db)
    row = {
        "row_key": "hospital-row-001",
        "record_id": None,
        "expected_version": None,
        "operation": "CREATE",
        "hospital_code": "SYNC-H001",
        "hospital_name": "โรงพยาบาลจากชีต",
        "short_name": "รพ.ชีต",
        "notes": None,
    }
    first = process_hospital_submission(db, row, admin)
    db.flush()
    second = process_hospital_submission(db, row, admin)
    assert first.id == second.id
    assert first.status == SyncStatus.APPLIED
    hospital = db.get(Hospital, first.entity_id)
    assert hospital.hospital_name == "โรงพยาบาลจากชีต"
    outbound = db.query(SyncEvent).filter_by(direction="OUTBOUND", entity_id=hospital.id).one()
    assert outbound.status == SyncStatus.PENDING


def test_stale_sheet_version_is_preserved_as_conflict(db) -> None:
    admin = make_admin(db)
    hospital = Hospital(hospital_code="SYNC-H002", hospital_name="ชื่อปัจจุบัน")
    db.add(hospital)
    db.flush()
    event = process_hospital_submission(
        db,
        {
            "row_key": "hospital-row-002",
            "record_id": str(hospital.id),
            "expected_version": hospital.version + 3,
            "operation": "UPDATE",
            "hospital_code": hospital.hospital_code,
            "hospital_name": "ชื่อจากชีตที่ล้าสมัย",
        },
        admin,
    )
    db.flush()
    assert event.status == SyncStatus.CONFLICT
    assert hospital.hospital_name == "ชื่อปัจจุบัน"
    assert "version ปัจจุบัน" in event.last_error
    assert event.payload["hospital_name"] == "ชื่อจากชีตที่ล้าสมัย"


def test_duplicate_hospital_code_is_preserved_as_failed_submission(db) -> None:
    admin = make_admin(db)
    db.add(Hospital(hospital_code="SYNC-DUP", hospital_name="ข้อมูลเดิม"))
    db.flush()
    event = process_hospital_submission(
        db,
        {
            "row_key": "hospital-row-duplicate",
            "record_id": None,
            "expected_version": None,
            "operation": "CREATE",
            "hospital_code": "SYNC-DUP",
            "hospital_name": "ข้อมูลซ้ำจากชีต",
        },
        admin,
    )
    db.flush()
    assert event.status == SyncStatus.FAILED
    assert "database constraint" in event.last_error


def test_google_export_retries_then_fails_bounded(db) -> None:
    event = SyncEvent(
        idempotency_key="sheet-out:test",
        direction="OUTBOUND",
        entity_type="Hospitals_View",
        payload={"worksheet": "Hospitals_View", "rows": []},
        status=SyncStatus.PENDING,
    )
    db.add(event)
    db.flush()
    provider = FailingGoogleProvider()
    process_outbound_event(db, event, provider, max_attempts=2)
    assert event.status == SyncStatus.PENDING
    assert event.attempts == 1
    process_outbound_event(db, event, provider, max_attempts=2)
    assert event.status == SyncStatus.FAILED
    assert event.attempts == 2
    assert event.last_error == "quota exceeded"
