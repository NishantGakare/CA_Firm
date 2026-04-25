from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NotificationChannel, NotificationStatus


class NotificationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    task_id: UUID | None
    invoice_id: UUID | None
    channel: NotificationChannel
    status: NotificationStatus
    title: str
    message: str
    scheduled_for: datetime | None
    sent_at: datetime | None
    read_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class NotificationMarkReadRequest(BaseModel):
    notification_id: UUID


class ManualNotificationRequest(BaseModel):
    user_id: UUID
    title: str = Field(min_length=3, max_length=160)
    message: str = Field(min_length=3, max_length=2000)
    channel: NotificationChannel = NotificationChannel.IN_APP
