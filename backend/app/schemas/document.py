from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentAccessState, DocumentKind


class DocumentUploadInitRequest(BaseModel):
    task_id: UUID
    kind: DocumentKind
    original_filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=120)


class DocumentUploadInitResponse(BaseModel):
    document_id: UUID
    upload_url: str
    fields: dict[str, str]


class DocumentUploadCompleteRequest(BaseModel):
    document_id: UUID


class DocumentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    client_id: UUID
    uploaded_by_id: UUID
    kind: DocumentKind
    original_filename: str
    content_type: str
    file_size_bytes: int
    s3_bucket: str
    s3_key: str
    access_state: DocumentAccessState
    approved_for_release: bool
    is_latest: bool
    released_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DocumentReleaseRequest(BaseModel):
    document_id: UUID
    release: bool = True


class DocumentDownloadResponse(BaseModel):
    download_url: str
    expires_in_seconds: int
