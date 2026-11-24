import argparse
import getpass

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.domain.enums import Role
from app.domain.models import User


def create_admin(
    db: Session,
    *,
    username: str | None = None,
    email: str | None = None,
    display_name: str,
    password: str,
) -> User:
    if username is None:
        if email is None:
            raise ValueError("User ID จำเป็น")
        try:
            normalized_username = validate_email(email.strip(), check_deliverability=False).normalized.lower()
        except EmailNotValidError as exc:
            raise ValueError("อีเมล Admin ไม่ถูกต้อง") from exc
        normalized_email = normalized_username
    else:
        normalized_username = username.strip().lower()
        if not normalized_username or any(char.isspace() for char in normalized_username):
            raise ValueError("User ID ต้องไม่ว่างและห้ามมีช่องว่าง")
        normalized_email = f"{normalized_username}@local.invalid" if email is None else email.strip().lower()
    normalized_name = display_name.strip()
    if not normalized_name:
        raise ValueError("ชื่อที่แสดงจำเป็น")
    local_default_admin = normalized_username == "admin" and password == "admin" and get_settings().app_env != "production"
    if len(password) < 4 and not local_default_admin:
        raise ValueError("รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษร")
    if db.scalar(select(User).where((User.username == normalized_username) | (User.email == normalized_email))):
        raise ValueError("มีอีเมลนี้แล้ว" if username is None else "มี User ID นี้แล้ว")
    user = User(
        username=normalized_username,
        email=normalized_email,
        display_name=normalized_name,
        password_hash=hash_password(password),
        role=Role.ADMIN,
    )
    db.add(user)
    db.flush()
    return user


def ensure_admin(db: Session, *, username: str = "admin", display_name: str = "Admin", password: str = "admin") -> User:
    normalized_username = username.strip().lower()
    user = db.scalar(select(User).where(User.username == normalized_username))
    if user:
        user.role = Role.ADMIN
        user.active = True
        user.display_name = display_name.strip() or "Admin"
        user.password_hash = hash_password(password)
        db.flush()
        return user
    return create_admin(db, username=normalized_username, display_name=display_name, password=password)


def bootstrap_admin_interactive() -> None:
    username = input("User ID Admin [admin]: ").strip() or "admin"
    display_name = input("ชื่อที่แสดง: ")
    password = getpass.getpass("รหัสผ่าน: ")
    try:
        with SessionLocal.begin() as db:
            create_admin(db, username=username, display_name=display_name, password=password)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print("สร้าง Admin สำเร็จ")


def main() -> None:
    parser = argparse.ArgumentParser(description="BA Chiller administration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("bootstrap-admin", help="สร้างผู้ดูแลระบบคนแรกแบบ interactive")
    subparsers.add_parser("ensure-admin", help="ซ่อม/ตั้งค่า User ID admin ให้เป็น Admin สำหรับ local development")
    args = parser.parse_args()
    if args.command == "bootstrap-admin":
        bootstrap_admin_interactive()
    if args.command == "ensure-admin":
        with SessionLocal.begin() as db:
            ensure_admin(db)
        print("ตั้งค่า admin สำเร็จ")


if __name__ == "__main__":
    main()
