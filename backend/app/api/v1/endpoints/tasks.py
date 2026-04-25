from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import require_ca_admin, require_client, require_staff
from app.db.session import get_db
from app.models.enums import TaskStatus
from app.models.user import User
from app.schemas.task import (
    CAReviewRequest,
    StaffTaskStatusUpdateRequest,
    TaskAssignRequest,
    TaskCreateRequest,
    TaskPublic,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("", response_model=TaskPublic, status_code=status.HTTP_201_CREATED)
def create_client_task_request(
    payload: TaskCreateRequest,
    current_user: User = Depends(require_client),
    db: Session = Depends(get_db),
) -> TaskPublic:
    service = TaskService(db)
    try:
        task = service.create_from_client_request(client=current_user, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return TaskPublic.model_validate(task)


@router.get("", response_model=list[TaskPublic])
def list_tasks(
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    client_id: UUID | None = Query(default=None),
    staff_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskPublic]:
    service = TaskService(db)
    tasks = service.list_visible_tasks(
        current_user=current_user,
        status=status_filter,
        client_id=client_id,
        staff_id=staff_id,
    )
    return [TaskPublic.model_validate(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskPublic)
def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskPublic:
    service = TaskService(db)
    try:
        task = service.get_visible_task(current_user=current_user, task_id=task_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return TaskPublic.model_validate(task)


@router.post("/{task_id}/assign", response_model=TaskPublic)
def assign_task_to_staff(
    task_id: UUID,
    payload: TaskAssignRequest,
    current_user: User = Depends(require_ca_admin),
    db: Session = Depends(get_db),
) -> TaskPublic:
    service = TaskService(db)
    try:
        task = service.assign_staff(ca_user=current_user, task_id=task_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return TaskPublic.model_validate(task)


@router.post("/{task_id}/staff-status", response_model=TaskPublic)
def update_task_status_by_staff(
    task_id: UUID,
    payload: StaffTaskStatusUpdateRequest,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> TaskPublic:
    service = TaskService(db)
    try:
        task = service.update_staff_status(staff_user=current_user, task_id=task_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return TaskPublic.model_validate(task)


@router.post("/{task_id}/ca-review", response_model=TaskPublic)
def review_task_by_ca(
    task_id: UUID,
    payload: CAReviewRequest,
    current_user: User = Depends(require_ca_admin),
    db: Session = Depends(get_db),
) -> TaskPublic:
    service = TaskService(db)
    try:
        task = service.ca_review(ca_user=current_user, task_id=task_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return TaskPublic.model_validate(task)
