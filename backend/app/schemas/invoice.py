from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import InvoiceStatus


class InvoiceCreateRequest(BaseModel):
    task_id: UUID
    sub_total: Decimal = Field(ge=0)
    tax_total: Decimal = Field(default=Decimal("0.00"), ge=0)
    discount_total: Decimal = Field(default=Decimal("0.00"), ge=0)
    due_date: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)


class InvoicePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_number: str
    task_id: UUID
    client_id: UUID
    issued_by_id: UUID
    currency: str
    sub_total: Decimal
    tax_total: Decimal
    discount_total: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    status: InvoiceStatus
    due_date: datetime | None
    issued_at: datetime | None
    paid_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
