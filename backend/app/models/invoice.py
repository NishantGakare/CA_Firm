from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import InvoiceStatus

if TYPE_CHECKING:
    from app.models.notification import Notification
    from app.models.payment import Payment
    from app.models.task import Task
    from app.models.user import User


class Invoice(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="invoice_total_non_negative"),
        CheckConstraint("amount_paid >= 0", name="invoice_paid_non_negative"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_client_id", "client_id"),
        Index("ix_invoices_due_date", "due_date"),
    )

    invoice_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)

    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id", ondelete="RESTRICT"), nullable=False, unique=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    issued_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR", server_default="INR")

    sub_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    balance_due: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    status: Mapped[InvoiceStatus] = mapped_column(
        SAEnum(InvoiceStatus, name="invoice_status"),
        nullable=False,
        default=InvoiceStatus.DRAFT,
        server_default=InvoiceStatus.DRAFT.value,
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    task: Mapped[Task] = relationship("Task", back_populates="invoice")
    client: Mapped[User] = relationship("User", foreign_keys=[client_id], back_populates="invoices_as_client")
    issued_by: Mapped[User] = relationship("User", foreign_keys=[issued_by_id], back_populates="invoices_issued")
    payments: Mapped[list[Payment]] = relationship("Payment", back_populates="invoice")
    notifications: Mapped[list[Notification]] = relationship("Notification", back_populates="invoice")
