from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

from botocore.exceptions import ClientError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.s3.client import get_s3_client
from app.integrations.s3.downloader import generate_presigned_download
from app.integrations.s3.uploader import generate_presigned_upload
from app.models.document import Document
from app.models.enums import DocumentAccessState, DocumentKind, InvoiceStatus, TaskStatus, UserRole
from app.models.task import Task
from app.models.user import User
from app.schemas.document import DocumentUploadInitRequest
from app.services.notification_service import NotificationService


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.notification_service = NotificationService(db)

    def initiate_upload(self, *, current_user: User, payload: DocumentUploadInitRequest) -> tuple[Document, dict[str, object]]:
        task = self.db.get(Task, payload.task_id)
        if task is None or task.deleted_at is not None:
            raise ValueError("Task not found")

        self._enforce_upload_permission(current_user=current_user, task=task, kind=payload.kind)

        object_key = self._build_object_key(task_id=task.id, user_id=current_user.id, filename=payload.original_filename)

        if payload.kind == DocumentKind.FINAL_DELIVERABLE:
            access_state = DocumentAccessState.LOCKED
        elif current_user.role in {UserRole.CA_ADMIN, UserRole.STAFF}:
            access_state = DocumentAccessState.UNLOCKED
        else:
            access_state = DocumentAccessState.LOCKED

        document = Document(
            task_id=task.id,
            client_id=task.client_id,
            uploaded_by_id=current_user.id,
            kind=payload.kind,
            original_filename=payload.original_filename,
            content_type=payload.content_type,
            file_size_bytes=0,
            s3_bucket=self.settings.s3_bucket_name,
            s3_key=object_key,
            access_state=access_state,
            approved_for_release=False,
            is_latest=True,
        )

        self.db.execute(
            update(Document)
            .where(
                Document.task_id == task.id,
                Document.kind == payload.kind,
                Document.is_latest.is_(True),
            )
            .values(is_latest=False)
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        if self.settings.storage_mode == "mock":
            presigned_post = {
                "url": f"{self.settings.app_base_url}/mock-storage/upload/{document.id}",
                "fields": {},
            }
        else:
            presigned_post = generate_presigned_upload(object_key=object_key, content_type=payload.content_type)
        return document, presigned_post

    def complete_upload(self, *, current_user: User, document_id: UUID) -> Document:
        document = self.db.get(Document, document_id)
        if document is None or document.deleted_at is not None:
            raise ValueError("Document not found")

        task = self.db.get(Task, document.task_id)
        if task is None or task.deleted_at is not None:
            raise ValueError("Task not found")

        self._enforce_upload_permission(current_user=current_user, task=task, kind=document.kind)

        if self.settings.storage_mode == "mock":
            document.file_size_bytes = max(document.file_size_bytes, 1024)
            if not document.checksum_sha256:
                document.checksum_sha256 = uuid4().hex
        else:
            s3 = get_s3_client()
            try:
                metadata = s3.head_object(Bucket=document.s3_bucket, Key=document.s3_key)
            except ClientError as exc:
                raise ValueError("Uploaded object not found in storage") from exc

            document.file_size_bytes = int(metadata.get("ContentLength", 0))
            document.checksum_sha256 = metadata.get("ETag", "").replace('"', "") or None

        self.db.commit()
        self.db.refresh(document)
        return document

    def list_visible_documents(self, *, current_user: User, task_id: UUID) -> list[Document]:
        task = self.db.get(Task, task_id)
        if task is None or task.deleted_at is not None:
            raise ValueError("Task not found")

        self._enforce_task_visibility(current_user=current_user, task=task)

        stmt = (
            select(Document)
            .where(Document.task_id == task_id, Document.deleted_at.is_(None))
            .order_by(Document.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def generate_download_url(self, *, current_user: User, document_id: UUID) -> str:
        document = self.db.get(Document, document_id)
        if document is None or document.deleted_at is not None:
            raise ValueError("Document not found")

        task = self.db.get(Task, document.task_id)
        if task is None or task.deleted_at is not None:
            raise ValueError("Task not found")

        if current_user.role == UserRole.CA_ADMIN:
            return self._build_download_link(document)

        if current_user.role == UserRole.STAFF:
            if task.assigned_staff_id != current_user.id:
                raise PermissionError("You do not have access to this document")
            return self._build_download_link(document)

        if current_user.role == UserRole.CLIENT:
            if task.client_id != current_user.id:
                raise PermissionError("You do not have access to this document")
            if not self._is_client_download_allowed(task=task, document=document):
                raise PermissionError("Document is locked until CA approval and payment")
            return self._build_download_link(document)

        raise PermissionError("Unsupported role")

    def release_document(self, *, ca_user: User, document_id: UUID, release: bool) -> Document:
        if ca_user.role != UserRole.CA_ADMIN:
            raise PermissionError("Only CA admin can release documents")

        document = self.db.get(Document, document_id)
        if document is None or document.deleted_at is not None:
            raise ValueError("Document not found")

        task = self.db.get(Task, document.task_id)
        if task is None or task.deleted_at is not None:
            raise ValueError("Task not found")

        if release:
            if task.status not in {TaskStatus.APPROVED_BY_CA, TaskStatus.INVOICED, TaskStatus.PAYMENT_PENDING, TaskStatus.PAYMENT_CONFIRMED, TaskStatus.DOCUMENT_RELEASED, TaskStatus.CLOSED}:
                raise ValueError("Task must be CA approved before release")

            invoice = task.invoice
            if invoice is None or invoice.status != InvoiceStatus.PAID:
                raise ValueError("Invoice must be paid before releasing document")

            document.approved_for_release = True
            document.access_state = DocumentAccessState.UNLOCKED
            document.released_at = datetime.now(UTC)

            if task.status in {TaskStatus.APPROVED_BY_CA, TaskStatus.INVOICED, TaskStatus.PAYMENT_PENDING, TaskStatus.PAYMENT_CONFIRMED}:
                task.status = TaskStatus.DOCUMENT_RELEASED
                task.document_released_at = datetime.now(UTC)
            self.notification_service.on_document_released(client_id=task.client_id, task_id=task.id)
        else:
            document.approved_for_release = False
            document.access_state = DocumentAccessState.LOCKED
            document.released_at = None

        self.db.commit()
        self.db.refresh(document)
        return document

    def _build_object_key(self, *, task_id: UUID, user_id: UUID, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        return f"tasks/{task_id}/users/{user_id}/{uuid4()}{ext}"

    def _enforce_upload_permission(self, *, current_user: User, task: Task, kind: DocumentKind) -> None:
        if current_user.role == UserRole.CA_ADMIN:
            return

        if current_user.role == UserRole.CLIENT:
            if task.client_id != current_user.id:
                raise PermissionError("You can upload documents only for your tasks")
            if kind != DocumentKind.CLIENT_INPUT:
                raise PermissionError("Client can upload only input documents")
            return

        if current_user.role == UserRole.STAFF:
            if task.assigned_staff_id != current_user.id:
                raise PermissionError("You can upload documents only for assigned tasks")
            if kind not in {DocumentKind.STAFF_WORKING, DocumentKind.STAFF_OUTPUT}:
                raise PermissionError("Staff can upload only working/output documents")
            return

        raise PermissionError("Unsupported role")

    def _enforce_task_visibility(self, *, current_user: User, task: Task) -> None:
        if current_user.role == UserRole.CA_ADMIN:
            return
        if current_user.role == UserRole.CLIENT and task.client_id == current_user.id:
            return
        if current_user.role == UserRole.STAFF and task.assigned_staff_id == current_user.id:
            return
        raise PermissionError("You do not have access to this task documents")

    def _is_client_download_allowed(self, *, task: Task, document: Document) -> bool:
        if not document.approved_for_release:
            return False
        if document.access_state != DocumentAccessState.UNLOCKED:
            return False
        invoice = task.invoice
        if invoice is None:
            return False
        if invoice.status != InvoiceStatus.PAID:
            return False
        return True

    def _build_download_link(self, document: Document) -> str:
        if self.settings.storage_mode == "mock":
            return f"{self.settings.app_base_url}/mock-storage/download/{document.id}"
        return generate_presigned_download(object_key=document.s3_key, filename=document.original_filename)
