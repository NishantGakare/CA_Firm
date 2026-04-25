from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TaskStatus


class TaskCreateRequest(BaseModel):
    service_id: UUID
    title: str = Field(min_length=3, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    due_date: datetime | None = None


class TaskAssignRequest(BaseModel):
    staff_user_id: UUID


class StaffTaskStatusUpdateRequest(BaseModel):
    status: TaskStatus
    note: str | None = Field(default=None, max_length=2000)


class CAReviewRequest(BaseModel):
    approve: bool
    comments: str | None = Field(default=None, max_length=3000)


class TaskListQuery(BaseModel):
    status: TaskStatus | None = None
    client_id: UUID | None = None
    staff_id: UUID | None = None


class TaskPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    client_id: UUID
    service_id: UUID
    assigned_staff_id: UUID | None
    reviewed_by_ca_id: UUID | None
    status: TaskStatus
    priority: str
    submitted_at: datetime
    due_date: datetime | None
    staff_completed_at: datetime | None
    ca_reviewed_at: datetime | None
    approved_at: datetime | None
    rejected_at: datetime | None
    payment_confirmed_at: datetime | None
    document_released_at: datetime | None
    created_at: datetime
    updated_at: datetime
