from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONDict
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentStatus

if TYPE_CHECKING:
    from app.models.invoice import Invoice
    from app.models.user import User


class Payment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="payment_amount_positive"),
        Index("ix_payments_status", "status"),
        Index("ix_payments_invoice_id", "invoice_id"),
        Index("ix_payments_provider_payment_id", "provider_payment_id"),
    )

    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR", server_default="INR")

    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status"),
        nullable=False,
        default=PaymentStatus.INITIATED,
        server_default=PaymentStatus.INITIATED.value,
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="RAZORPAY", server_default="RAZORPAY")

    provider_order_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True)
    provider_signature: Mapped[str | None] = mapped_column(String(255), nullable=True)

    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[JSONDict | None] = mapped_column(JSONB, nullable=True)

    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="payments")
    client: Mapped[User] = relationship("User", back_populates="payments")
