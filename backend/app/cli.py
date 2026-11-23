import argparse
import getpass

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.domain.enums import Role
from app.domain.models import User


def create_admin(
    db: Session,
    *,
    email: str,
    display_name: str,
    password: str,
) -> User:
    try:
        normalized_email = validate_email(email.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        raise ValueError("อีเมล Admin ไม่ถูกต้อง") from exc
    normalized_name = display_name.strip()
    if not normalized_name:
        raise ValueError("ชื่อที่แสดงจำเป็น")
    if len(password) < 12:
        raise ValueError("รหัสผ่านต้องมีอย่างน้อย 12 ตัวอักษร")
    if db.scalar(select(User).where(User.email == normalized_email)):
        raise ValueError("มีผู้ใช้อีเมลนี้แล้ว")
    user = User(
        email=normalized_email,
        display_name=normalized_name,
        password_hash=hash_password(password),
        role=Role.ADMIN,
    )
    db.add(user)
    db.flush()
    return user


def bootstrap_admin_interactive() -> None:
    email = input("อีเมล Admin: ")
    display_name = input("ชื่อที่แสดง: ")
    password = getpass.getpass("รหัสผ่าน (อย่างน้อย 12 ตัวอักษร): ")
    try:
        with SessionLocal.begin() as db:
            create_admin(db, email=email, display_name=display_name, password=password)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print("สร้าง Admin สำเร็จ")


def main() -> None:
    parser = argparse.ArgumentParser(description="BA Chiller administration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("bootstrap-admin", help="สร้างผู้ดูแลระบบคนแรกแบบ interactive")
    args = parser.parse_args()
    if args.command == "bootstrap-admin":
        bootstrap_admin_interactive()


if __name__ == "__main__":
    main()
