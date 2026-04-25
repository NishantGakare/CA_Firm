from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.payments.factory import get_payment_gateway
from app.models.enums import InvoiceStatus, PaymentStatus, TaskStatus, UserRole
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.task import Task
from app.models.user import User
from app.schemas.invoice import InvoiceCreateRequest
from app.schemas.payment import PaymentInitiateRequest, PaymentVerifyRequest
from app.services.notification_service import NotificationService


class BillingService:
    def __init__(self, db: Session):
        self.db = db
        self.gateway = get_payment_gateway()
        self.notification_service = NotificationService(db)

    def create_invoice(self, *, ca_user: User, payload: InvoiceCreateRequest) -> Invoice:
        if ca_user.role != UserRole.CA_ADMIN:
            raise PermissionError("Only CA admin can create invoices")

        task = self.db.get(Task, payload.task_id)
        if task is None or task.deleted_at is not None:
            raise ValueError("Task not found")
        if task.status != TaskStatus.APPROVED_BY_CA:
            raise ValueError("Invoice can be created only after CA approval")
        if task.invoice is not None:
            raise ValueError("Invoice already exists for this task")

        total = payload.sub_total + payload.tax_total - payload.discount_total
        if total < 0:
            raise ValueError("Total amount cannot be negative")

        now = datetime.now(UTC)
        invoice = Invoice(
            invoice_number=self._next_invoice_number(now),
            task_id=task.id,
            client_id=task.client_id,
            issued_by_id=ca_user.id,
            sub_total=payload.sub_total,
            tax_total=payload.tax_total,
            discount_total=payload.discount_total,
            total_amount=total,
            amount_paid=Decimal("0.00"),
            balance_due=total,
            status=InvoiceStatus.ISSUED,
            due_date=payload.due_date,
            issued_at=now,
            notes=payload.notes,
        )
        self.db.add(invoice)

        task.status = TaskStatus.PAYMENT_PENDING

        self.notification_service.on_invoice_issued(
            client_id=invoice.client_id,
            task_id=task.id,
            invoice_id=invoice.id,
            invoice_number=invoice.invoice_number,
        )

        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def list_visible_invoices(self, *, current_user: User) -> list[Invoice]:
        stmt = select(Invoice).where(Invoice.deleted_at.is_(None)).order_by(Invoice.created_at.desc())
        if current_user.role == UserRole.CLIENT:
            stmt = stmt.where(Invoice.client_id == current_user.id)
        return list(self.db.scalars(stmt).all())

    def initiate_payment(self, *, client_user: User, payload: PaymentInitiateRequest) -> Payment:
        if client_user.role != UserRole.CLIENT:
            raise PermissionError("Only clients can initiate payments")

        invoice = self.db.get(Invoice, payload.invoice_id)
        if invoice is None or invoice.deleted_at is not None:
            raise ValueError("Invoice not found")
        if invoice.client_id != client_user.id:
            raise PermissionError("Invoice does not belong to this client")
        if invoice.status in {InvoiceStatus.PAID, InvoiceStatus.VOID}:
            raise ValueError("Payment cannot be initiated for this invoice status")
        if payload.amount > invoice.balance_due:
            raise ValueError("Payment amount exceeds balance due")

        provider_order_id = self.gateway.create_order(
            amount=payload.amount,
            currency=invoice.currency,
            receipt=invoice.invoice_number,
        )

        payment = Payment(
            invoice_id=invoice.id,
            client_id=client_user.id,
            amount=payload.amount,
            currency=invoice.currency,
            status=PaymentStatus.INITIATED,
            provider="MOCK",
            provider_order_id=provider_order_id,
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def verify_payment(self, *, client_user: User, payload: PaymentVerifyRequest) -> Payment:
        if client_user.role != UserRole.CLIENT:
            raise PermissionError("Only clients can verify payments")

        payment = self.db.get(Payment, payload.payment_id)
        if payment is None:
            raise ValueError("Payment not found")
        if payment.client_id != client_user.id:
            raise PermissionError("Payment does not belong to this client")
        if payment.status != PaymentStatus.INITIATED:
            raise ValueError("Payment is not in INITIATED state")

        invoice = self.db.get(Invoice, payment.invoice_id)
        if invoice is None or invoice.deleted_at is not None:
            raise ValueError("Invoice not found")

        verified = payload.success and self.gateway.verify(
            provider_payment_id=payload.provider_payment_id,
            provider_order_id=payment.provider_order_id or "",
            signature=payload.provider_signature,
        )

        now = datetime.now(UTC)
        payment.provider_payment_id = payload.provider_payment_id
        payment.provider_signature = payload.provider_signature

        if not verified:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = "Verification failed"
            self.db.commit()
            self.db.refresh(payment)
            return payment

        payment.status = PaymentStatus.SUCCEEDED
        payment.paid_at = now

        invoice.amount_paid = (invoice.amount_paid or Decimal("0.00")) + payment.amount
        invoice.balance_due = max(Decimal("0.00"), invoice.total_amount - invoice.amount_paid)

        task = invoice.task
        if invoice.balance_due == Decimal("0.00"):
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = now
            if task is not None:
                task.status = TaskStatus.PAYMENT_CONFIRMED
                task.payment_confirmed_at = now
                self.notification_service.on_payment_confirmed(
                    client_id=invoice.client_id,
                    task_id=task.id,
                    invoice_id=invoice.id,
                )
        else:
            invoice.status = InvoiceStatus.PARTIALLY_PAID
            if task is not None:
                task.status = TaskStatus.PAYMENT_PENDING

        self.db.commit()
        self.db.refresh(payment)
        return payment

    def _next_invoice_number(self, now: datetime) -> str:
        prefix = now.strftime("INV-%Y%m")
        count_stmt = select(Invoice).where(Invoice.invoice_number.like(f"{prefix}-%"))
        serial = len(list(self.db.scalars(count_stmt).all())) + 1
        return f"{prefix}-{serial:04d}"
