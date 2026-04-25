from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_ca_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.invoice import InvoiceCreateRequest, InvoicePublic
from app.services.billing_service import BillingService

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.post("", response_model=InvoicePublic, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreateRequest,
    current_user: User = Depends(require_ca_admin),
    db: Session = Depends(get_db),
) -> InvoicePublic:
    service = BillingService(db)
    try:
        invoice = service.create_invoice(ca_user=current_user, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return InvoicePublic.model_validate(invoice)


@router.get("", response_model=list[InvoicePublic])
def list_invoices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InvoicePublic]:
    service = BillingService(db)
    invoices = service.list_visible_invoices(current_user=current_user)
    return [InvoicePublic.model_validate(inv) for inv in invoices]
