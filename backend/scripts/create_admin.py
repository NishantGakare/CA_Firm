from __future__ import annotations

import os

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.user import User


def main() -> None:
    email = os.getenv("ADMIN_EMAIL", "ca.admin@cafirm.local").lower()
    password = os.getenv("ADMIN_PASSWORD", "ChangeMe@123")
    full_name = os.getenv("ADMIN_NAME", "CA Admin")

    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.email == email))
        if existing is not None:
            existing.password_hash = hash_password(password)
            existing.role = UserRole.CA_ADMIN
            existing.is_active = True
            db.commit()
            print(f"Updated existing admin: {email}")
            return

        admin = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.CA_ADMIN,
            is_active=True,
            is_verified=True,
        )
        db.add(admin)
        db.commit()
        print(f"Created admin: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
