from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ApprovalDecision

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User


class TaskApproval(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "task_approvals"
    __table_args__ = (
        Index("ix_task_approvals_task_id", "task_id"),
        Index("ix_task_approvals_reviewed_by_id", "reviewed_by_id"),
    )

    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    reviewed_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    round_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    decision: Mapped[ApprovalDecision] = mapped_column(
        SAEnum(ApprovalDecision, name="approval_decision"),
        nullable=False,
    )
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    task: Mapped[Task] = relationship("Task", back_populates="approvals")
    reviewed_by: Mapped[User] = relationship("User", back_populates="approvals_done")
