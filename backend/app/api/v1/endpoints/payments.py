from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.rbac import require_client
from app.db.session import get_db
from app.models.user import User
from app.schemas.payment import (
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentPublic,
    PaymentVerifyRequest,
)
from app.services.billing_service import BillingService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/initiate", response_model=PaymentInitiateResponse, status_code=status.HTTP_201_CREATED)
def initiate_payment(
    payload: PaymentInitiateRequest,
    current_user: User = Depends(require_client),
    db: Session = Depends(get_db),
) -> PaymentInitiateResponse:
    service = BillingService(db)
    try:
        payment = service.initiate_payment(client_user=current_user, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return PaymentInitiateResponse(
        payment_id=payment.id,
        provider=payment.provider,
        provider_order_id=payment.provider_order_id or "",
        amount=payment.amount,
        currency=payment.currency,
    )


@router.post("/verify", response_model=PaymentPublic)
def verify_payment(
    payload: PaymentVerifyRequest,
    current_user: User = Depends(require_client),
    db: Session = Depends(get_db),
) -> PaymentPublic:
    service = BillingService(db)
    try:
        payment = service.verify_payment(client_user=current_user, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return PaymentPublic.model_validate(payment)
