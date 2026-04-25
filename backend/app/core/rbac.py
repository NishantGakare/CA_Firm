from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.enums import UserRole
from app.models.user import User


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    allowed = set(allowed_roles)

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return dependency


require_ca_admin = require_roles(UserRole.CA_ADMIN)
require_staff = require_roles(UserRole.STAFF)
require_client = require_roles(UserRole.CLIENT)
require_ca_or_staff = require_roles(UserRole.CA_ADMIN, UserRole.STAFF)


def enforce_self_or_ca(current_user: User, target_user_id: UUID) -> None:
    if current_user.role == UserRole.CA_ADMIN:
        return
    if current_user.id != target_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own resources",
        )


def enforce_task_visibility(
    *,
    current_user: User,
    task_client_id: UUID,
    task_staff_id: UUID | None,
) -> None:
    if current_user.role == UserRole.CA_ADMIN:
        return

    if current_user.role == UserRole.CLIENT and current_user.id == task_client_id:
        return

    if current_user.role == UserRole.STAFF and task_staff_id is not None and current_user.id == task_staff_id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this task",
    )
