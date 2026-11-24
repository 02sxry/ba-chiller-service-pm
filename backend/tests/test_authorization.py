from fastapi.testclient import TestClient

from app.core.db import get_db
from app.core.security import create_access_token
from app.domain.enums import Role
from app.domain.models import Hospital, User
from app.main import app


def make_user(db, email: str, role: Role) -> User:
    user = User(email=email, password_hash="unused", display_name=email, role=role)
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
            json={"hospital_code": "AUTH-H2", "hospital_name": "โรงพยาบาลมีสิทธิ์"},
        )
        assert response.status_code == 201
        assert response.json()["hospital_code"] == "AUTH-H2"
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
