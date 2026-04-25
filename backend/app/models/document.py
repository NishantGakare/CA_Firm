from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import DocumentAccessState, DocumentKind

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_task_id", "task_id"),
        Index("ix_documents_client_id", "client_id"),
        Index("ix_documents_access_state", "access_state"),
        Index("ix_documents_is_latest", "is_latest"),
    )

    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    uploaded_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    kind: Mapped[DocumentKind] = mapped_column(SAEnum(DocumentKind, name="document_kind"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    s3_bucket: Mapped[str] = mapped_column(String(120), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    s3_version_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    access_state: Mapped[DocumentAccessState] = mapped_column(
        SAEnum(DocumentAccessState, name="document_access_state"),
        nullable=False,
        default=DocumentAccessState.LOCKED,
        server_default=DocumentAccessState.LOCKED.value,
    )
    approved_for_release: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task: Mapped[Task] = relationship("Task", back_populates="documents")
    uploaded_by: Mapped[User] = relationship(
        "User",
        foreign_keys=[uploaded_by_id],
        back_populates="uploaded_documents",
    )
