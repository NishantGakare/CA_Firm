from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONDict
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import NotificationChannel, NotificationStatus

if TYPE_CHECKING:
    from app.models.invoice import Invoice
    from app.models.task import Task
    from app.models.user import User


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_status", "status"),
        Index("ix_notifications_scheduled_for", "scheduled_for"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[UUID | None] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    invoice_id: Mapped[UUID | None] = mapped_column(ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)

    channel: Mapped[NotificationChannel] = mapped_column(
        SAEnum(NotificationChannel, name="notification_channel"),
        nullable=False,
        default=NotificationChannel.IN_APP,
        server_default=NotificationChannel.IN_APP.value,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        SAEnum(NotificationStatus, name="notification_status"),
        nullable=False,
        default=NotificationStatus.PENDING,
        server_default=NotificationStatus.PENDING.value,
    )

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_json: Mapped[JSONDict | None] = mapped_column(JSONB, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="notifications")
    task: Mapped[Task | None] = relationship("Task", back_populates="notifications")
    invoice: Mapped[Invoice | None] = relationship("Invoice", back_populates="notifications")
