from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TaskStatus

if TYPE_CHECKING:
    from app.models.approval import TaskApproval
    from app.models.document import Document
    from app.models.invoice import Invoice
    from app.models.notification import Notification
    from app.models.service import ServiceCatalog
    from app.models.user import User


class Task(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_client_id", "client_id"),
        Index("ix_tasks_assigned_staff_id", "assigned_staff_id"),
        Index("ix_tasks_due_date", "due_date"),
    )

    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    service_id: Mapped[UUID] = mapped_column(ForeignKey("service_catalog.id", ondelete="RESTRICT"), nullable=False)

    assigned_staff_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_ca_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus, name="task_status"),
        nullable=False,
        default=TaskStatus.TODO,
        server_default=TaskStatus.TODO.value,
    )
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM", server_default="MEDIUM")

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    staff_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ca_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    document_released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    client: Mapped[User] = relationship("User", foreign_keys=[client_id], back_populates="tasks_as_client")
    assigned_staff: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[assigned_staff_id],
        back_populates="tasks_as_staff",
    )
    reviewed_by_ca: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[reviewed_by_ca_id],
        back_populates="tasks_reviewed_as_ca",
    )
    service: Mapped[ServiceCatalog] = relationship("ServiceCatalog", back_populates="tasks")

    approvals: Mapped[list[TaskApproval]] = relationship("TaskApproval", back_populates="task")
    documents: Mapped[list[Document]] = relationship("Document", back_populates="task")
    invoice: Mapped[Invoice | None] = relationship("Invoice", back_populates="task", uselist=False)
    notifications: Mapped[list[Notification]] = relationship("Notification", back_populates="task")
