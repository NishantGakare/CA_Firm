from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentStatus


class PaymentInitiateRequest(BaseModel):
    invoice_id: UUID
    amount: Decimal = Field(gt=0)


class PaymentInitiateResponse(BaseModel):
    payment_id: UUID
    provider: str
    provider_order_id: str
    amount: Decimal
    currency: str


class PaymentVerifyRequest(BaseModel):
    payment_id: UUID
    provider_payment_id: str = Field(min_length=3, max_length=120)
    provider_signature: str | None = Field(default=None, max_length=255)
    success: bool = True


class PaymentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_id: UUID
    client_id: UUID
    amount: Decimal
    currency: str
    status: PaymentStatus
    provider: str
    provider_order_id: str | None
    provider_payment_id: str | None
    paid_at: datetime | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
