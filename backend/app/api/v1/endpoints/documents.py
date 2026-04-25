from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rbac import require_ca_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.document import (
    DocumentDownloadResponse,
    DocumentPublic,
    DocumentReleaseRequest,
    DocumentUploadCompleteRequest,
    DocumentUploadInitRequest,
    DocumentUploadInitResponse,
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload/init", response_model=DocumentUploadInitResponse, status_code=status.HTTP_201_CREATED)
def initiate_upload(
    payload: DocumentUploadInitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentUploadInitResponse:
    service = DocumentService(db)
    try:
        document, post_data = service.initiate_upload(current_user=current_user, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return DocumentUploadInitResponse(
        document_id=document.id,
        upload_url=str(post_data["url"]),
        fields={k: str(v) for k, v in dict(post_data["fields"]).items()},
    )


@router.post("/upload/complete", response_model=DocumentPublic)
def complete_upload(
    payload: DocumentUploadCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentPublic:
    service = DocumentService(db)
    try:
        document = service.complete_upload(current_user=current_user, document_id=payload.document_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return DocumentPublic.model_validate(document)


@router.get("/task/{task_id}", response_model=list[DocumentPublic])
def list_task_documents(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentPublic]:
    service = DocumentService(db)
    try:
        docs = service.list_visible_documents(current_user=current_user, task_id=task_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return [DocumentPublic.model_validate(doc) for doc in docs]


@router.get("/{document_id}/download", response_model=DocumentDownloadResponse)
def generate_download_link(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentDownloadResponse:
    service = DocumentService(db)
    try:
        url = service.generate_download_url(current_user=current_user, document_id=document_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return DocumentDownloadResponse(download_url=url, expires_in_seconds=get_settings().s3_presigned_expire_seconds)


@router.post("/release", response_model=DocumentPublic)
def release_document(
    payload: DocumentReleaseRequest,
    current_user: User = Depends(require_ca_admin),
    db: Session = Depends(get_db),
) -> DocumentPublic:
    service = DocumentService(db)
    try:
        document = service.release_document(ca_user=current_user, document_id=payload.document_id, release=payload.release)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return DocumentPublic.model_validate(document)
