from fastapi.testclient import TestClient

from app.core.db import get_db
from app.core.security import create_access_token
from app.domain.enums import Role
from app.domain.models import User
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
