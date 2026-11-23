import pytest

from app.cli import create_admin
from app.core.security import verify_password
from app.domain.enums import Role


def test_create_admin_normalizes_and_hashes_password(db) -> None:
    user = create_admin(
        db,
        email="  FIRST.ADMIN@EXAMPLE.COM ",
        display_name="  ผู้ดูแลระบบ ",
        password="long-secure-password",
    )
    assert user.email == "first.admin@example.com"
    assert user.display_name == "ผู้ดูแลระบบ"
    assert user.role == Role.ADMIN
    assert verify_password("long-secure-password", user.password_hash)


def test_create_admin_rejects_short_password_and_duplicate_email(db) -> None:
    with pytest.raises(ValueError, match="อีเมล Admin"):
        create_admin(
            db,
            email="admin@example.invalid",
            display_name="Admin",
            password="long-secure-password",
        )
    with pytest.raises(ValueError, match="12"):
        create_admin(db, email="admin@example.com", display_name="Admin", password="short")
    create_admin(
        db,
        email="admin@example.com",
        display_name="Admin",
        password="long-secure-password",
    )
    with pytest.raises(ValueError, match="อีเมลนี้แล้ว"):
        create_admin(
            db,
            email="ADMIN@example.com",
            display_name="Another Admin",
            password="another-secure-password",
        )
