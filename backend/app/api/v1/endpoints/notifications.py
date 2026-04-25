from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import (
    ManualNotificationRequest,
    NotificationMarkReadRequest,
    NotificationPublic,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/me", response_model=list[NotificationPublic])
def list_my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotificationPublic]:
    service = NotificationService(db)
    items = service.list_for_user(user=current_user)
    return [NotificationPublic.model_validate(i) for i in items]


@router.post("/read", response_model=NotificationPublic)
def mark_notification_read(
    payload: NotificationMarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationPublic:
    service = NotificationService(db)
    try:
        item = service.mark_read(user=current_user, notification_id=payload.notification_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return NotificationPublic.model_validate(item)


@router.post("/manual", response_model=NotificationPublic, status_code=status.HTTP_201_CREATED)
def send_manual_notification(
    payload: ManualNotificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationPublic:
    service = NotificationService(db)
    try:
        item = service.manual_notify(
            actor=current_user,
            target_user_id=payload.user_id,
            title=payload.title,
            message=payload.message,
            channel=payload.channel,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return NotificationPublic.model_validate(item)
