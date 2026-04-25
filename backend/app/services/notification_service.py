from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import NotificationChannel, NotificationStatus, UserRole
from app.models.notification import Notification
from app.models.user import User


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def create_notification(
        self,
        *,
        user_id: UUID,
        title: str,
        message: str,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        task_id: UUID | None = None,
        invoice_id: UUID | None = None,
        metadata_json: dict | None = None,
    ) -> Notification:
        status = NotificationStatus.SENT if channel == NotificationChannel.IN_APP else NotificationStatus.PENDING
        sent_at = datetime.now(UTC) if channel == NotificationChannel.IN_APP else None

        n = Notification(
            user_id=user_id,
            task_id=task_id,
            invoice_id=invoice_id,
            channel=channel,
            status=status,
            title=title,
            message=message,
            sent_at=sent_at,
            metadata_json=metadata_json,
        )
        self.db.add(n)
        self.db.flush()
        return n

    def list_for_user(self, *, user: User) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def mark_read(self, *, user: User, notification_id: UUID) -> Notification:
        n = self.db.get(Notification, notification_id)
        if n is None:
            raise ValueError("Notification not found")
        if n.user_id != user.id and user.role != UserRole.CA_ADMIN:
            raise PermissionError("You do not have access to this notification")

        if n.read_at is None:
            n.read_at = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(n)
        return n

    def manual_notify(
        self,
        *,
        actor: User,
        target_user_id: UUID,
        title: str,
        message: str,
        channel: NotificationChannel,
    ) -> Notification:
        if actor.role not in {UserRole.CA_ADMIN, UserRole.STAFF}:
            raise PermissionError("Only CA or staff can send manual reminders")

        target = self.db.get(User, target_user_id)
        if target is None or not target.is_active:
            raise ValueError("Target user not found")

        self.create_notification(
            user_id=target.id,
            title=title,
            message=message,
            channel=channel,
            metadata_json={"source": "manual", "actor_user_id": str(actor.id)},
        )
        self.db.commit()

        created = self.db.scalars(
            select(Notification)
            .where(Notification.user_id == target.id)
            .order_by(Notification.created_at.desc())
        ).first()
        if created is None:
            raise ValueError("Could not create notification")
        return created

    # Event helpers
    def on_task_created(self, *, client_id: UUID, task_id: UUID, task_title: str) -> None:
        self.create_notification(
            user_id=client_id,
            task_id=task_id,
            title="Task Created",
            message=f"Your service request '{task_title}' has been created.",
        )

    def on_task_assigned(self, *, staff_id: UUID, task_id: UUID, task_title: str) -> None:
        self.create_notification(
            user_id=staff_id,
            task_id=task_id,
            title="Task Assigned",
            message=f"A new task '{task_title}' has been assigned to you.",
        )

    def on_task_sent_for_review(self, *, client_id: UUID, task_id: UUID) -> None:
        self.create_notification(
            user_id=client_id,
            task_id=task_id,
            title="Task Under CA Review",
            message="Your task has been completed by staff and is now under CA review.",
        )

    def on_task_reviewed(self, *, client_id: UUID, task_id: UUID, approved: bool) -> None:
        title = "Task Approved" if approved else "Task Rejected"
        message = (
            "Your task has been approved by CA."
            if approved
            else "Your task was rejected by CA and sent back for rework."
        )
        self.create_notification(user_id=client_id, task_id=task_id, title=title, message=message)

    def on_invoice_issued(self, *, client_id: UUID, task_id: UUID, invoice_id: UUID, invoice_number: str) -> None:
        self.create_notification(
            user_id=client_id,
            task_id=task_id,
            invoice_id=invoice_id,
            title="Invoice Issued",
            message=f"Invoice {invoice_number} has been issued. Please complete payment.",
        )

    def on_payment_confirmed(self, *, client_id: UUID, task_id: UUID, invoice_id: UUID) -> None:
        self.create_notification(
            user_id=client_id,
            task_id=task_id,
            invoice_id=invoice_id,
            title="Payment Confirmed",
            message="Your payment has been confirmed successfully.",
        )

    def on_document_released(self, *, client_id: UUID, task_id: UUID) -> None:
        self.create_notification(
            user_id=client_id,
            task_id=task_id,
            title="Document Released",
            message="Your finalized documents are now available for download.",
        )
