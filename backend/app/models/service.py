from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.task import Task


class ServiceCatalog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "service_catalog"
    __table_args__ = (
        Index("ix_service_catalog_active", "is_active"),
    )

    service_code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    base_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    sla_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    tasks: Mapped[list[Task]] = relationship("Task", back_populates="service")
