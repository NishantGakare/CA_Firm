from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.documents import router as documents_router
from app.api.v1.endpoints.invoices import router as invoices_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.payments import router as payments_router
from app.api.v1.endpoints.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(tasks_router)
api_router.include_router(documents_router)
api_router.include_router(invoices_router)
api_router.include_router(payments_router)
api_router.include_router(notifications_router)
