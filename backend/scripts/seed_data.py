from __future__ import annotations

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.service import ServiceCatalog
from app.models.user import User

DEFAULT_PASSWORD = "ChangeMe@123"


def seed_users(db):
    users_to_seed = [
        {
            "full_name": "CA Admin",
            "email": "ca.admin@cafirm.local",
            "role": UserRole.CA_ADMIN,
            "phone": "+91-9000000001",
        },
        {
            "full_name": "Staff One",
            "email": "staff1@cafirm.local",
            "role": UserRole.STAFF,
            "phone": "+91-9000000002",
        },
        {
            "full_name": "Client One",
            "email": "client1@cafirm.local",
            "role": UserRole.CLIENT,
            "phone": "+91-9000000003",
        },
    ]

    for item in users_to_seed:
        exists = db.scalar(select(User).where(User.email == item["email"]))
        if exists:
            continue

        user = User(
            full_name=item["full_name"],
            email=item["email"],
            phone=item["phone"],
            password_hash=hash_password(DEFAULT_PASSWORD),
            role=item["role"],
            is_active=True,
            is_verified=True,
        )
        db.add(user)


def seed_services(db):
    services = [
        {"service_code": "ITR", "name": "Income Tax Return Filing", "base_fee": 1500, "sla_days": 5},
        {"service_code": "GST", "name": "GST Return Filing", "base_fee": 2200, "sla_days": 4},
        {"service_code": "TDS", "name": "TDS Return Filing", "base_fee": 1800, "sla_days": 4},
        {"service_code": "AUDIT", "name": "Tax Audit Support", "base_fee": 7500, "sla_days": 10},
    ]

    for item in services:
        exists = db.scalar(select(ServiceCatalog).where(ServiceCatalog.service_code == item["service_code"]))
        if exists:
            continue

        db.add(
            ServiceCatalog(
                service_code=item["service_code"],
                name=item["name"],
                base_fee=item["base_fee"],
                sla_days=item["sla_days"],
                is_active=True,
            )
        )


def main() -> None:
    db = SessionLocal()
    try:
        seed_users(db)
        seed_services(db)
        db.commit()
        print("Seed completed.")
        print("Default password for seeded users:", DEFAULT_PASSWORD)
    finally:
        db.close()


if __name__ == "__main__":
    main()
