from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.approval import TaskApproval
    from app.models.document import Document
    from app.models.invoice import Invoice
    from app.models.notification import Notification
    from app.models.payment import Payment
    from app.models.refresh_token import RefreshToken
    from app.models.task import Task


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_role", "role"),
        Index("ix_users_is_active", "is_active"),
    )

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role"), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)

    tasks_as_client: Mapped[list[Task]] = relationship(
        "Task",
        foreign_keys="Task.client_id",
        back_populates="client",
    )
    tasks_as_staff: Mapped[list[Task]] = relationship(
        "Task",
        foreign_keys="Task.assigned_staff_id",
        back_populates="assigned_staff",
    )
    tasks_reviewed_as_ca: Mapped[list[Task]] = relationship(
        "Task",
        foreign_keys="Task.reviewed_by_ca_id",
        back_populates="reviewed_by_ca",
    )

    approvals_done: Mapped[list[TaskApproval]] = relationship("TaskApproval", back_populates="reviewed_by")
    uploaded_documents: Mapped[list[Document]] = relationship(
        "Document",
        foreign_keys="Document.uploaded_by_id",
        back_populates="uploaded_by",
    )

    invoices_as_client: Mapped[list[Invoice]] = relationship(
        "Invoice",
        foreign_keys="Invoice.client_id",
        back_populates="client",
    )
    invoices_issued: Mapped[list[Invoice]] = relationship(
        "Invoice",
        foreign_keys="Invoice.issued_by_id",
        back_populates="issued_by",
    )

    payments: Mapped[list[Payment]] = relationship("Payment", back_populates="client")
    refresh_tokens: Mapped[list[RefreshToken]] = relationship("RefreshToken", back_populates="user")
    notifications: Mapped[list[Notification]] = relationship("Notification", back_populates="user")
