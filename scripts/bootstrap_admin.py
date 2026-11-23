import getpass
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.domain.enums import Role  # noqa: E402
from app.domain.models import User  # noqa: E402


def main() -> None:
    email = input("อีเมล Admin: ").strip().lower()
    display_name = input("ชื่อที่แสดง: ").strip()
    password = getpass.getpass("รหัสผ่าน (อย่างน้อย 12 ตัวอักษร): ")
    if len(password) < 12:
        raise SystemExit("รหัสผ่านสั้นเกินไป")
    with SessionLocal.begin() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("มีผู้ใช้อีเมลนี้แล้ว")
        db.add(User(email=email, display_name=display_name, password_hash=hash_password(password), role=Role.ADMIN))
    print("สร้าง Admin สำเร็จ")


if __name__ == "__main__":
    main()

