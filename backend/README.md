# CA Firm Backend

Production-oriented FastAPI backend for CA firm management.

## Quick Start (Docker)

1. Build and start services:
   docker compose up --build
2. API will be available at:
   http://localhost:8000
3. Swagger docs:
   http://localhost:8000/docs

On startup, the API container runs:
- Alembic migration: `alembic upgrade head`
- Seed script: `python scripts/seed_data.py`
- API server: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

## Seeded Accounts

Default password for seeded users:
- `ChangeMe@123`

Seeded users:
- CA Admin: `ca.admin@cafirm.local`
- Staff: `staff1@cafirm.local`
- Client: `client1@cafirm.local`

## Local Dev (without Docker)

1. Create virtual environment and install dependencies:
   pip install -r requirements.txt
2. Configure environment variables (copy from `.env.example`)
3. Run migrations:
   alembic upgrade head
4. Seed data:
   python scripts/seed_data.py
5. Start API:
   uvicorn app.main:app --reload

## Notes

- `STORAGE_MODE=mock` is enabled for prototype testing without AWS S3.
- Payment flow uses mock payment gateway integration for local testing.
- For production, switch to real S3 and real payment gateway implementation.
