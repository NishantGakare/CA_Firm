from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.approval import TaskApproval
from app.models.enums import ApprovalDecision, TaskStatus, UserRole
from app.models.service import ServiceCatalog
from app.models.task import Task
from app.models.user import User
from app.schemas.task import (
    CAReviewRequest,
    StaffTaskStatusUpdateRequest,
    TaskAssignRequest,
    TaskCreateRequest,
)
from app.services.notification_service import NotificationService


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)

    def create_from_client_request(self, *, client: User, payload: TaskCreateRequest) -> Task:
        if client.role != UserRole.CLIENT:
            raise ValueError("Only clients can create service requests")

        service = self.db.get(ServiceCatalog, payload.service_id)
        if service is None or not service.is_active:
            raise ValueError("Selected service is unavailable")

        task = Task(
            title=payload.title.strip(),
            description=payload.description,
            client_id=client.id,
            service_id=service.id,
            status=TaskStatus.TODO,
            due_date=payload.due_date,
            submitted_at=datetime.now(UTC),
        )
        self.db.add(task)
        self.notification_service.on_task_created(client_id=client.id, task_id=task.id, task_title=task.title)
        self.db.commit()
        self.db.refresh(task)
        return task

    def list_visible_tasks(
        self,
        *,
        current_user: User,
        status: TaskStatus | None = None,
        client_id: UUID | None = None,
        staff_id: UUID | None = None,
    ) -> list[Task]:
        stmt = select(Task).where(Task.deleted_at.is_(None))

        if current_user.role == UserRole.CLIENT:
            stmt = stmt.where(Task.client_id == current_user.id)
        elif current_user.role == UserRole.STAFF:
            stmt = stmt.where(Task.assigned_staff_id == current_user.id)

        if status is not None:
            stmt = stmt.where(Task.status == status)

        if current_user.role == UserRole.CA_ADMIN:
            if client_id is not None:
                stmt = stmt.where(Task.client_id == client_id)
            if staff_id is not None:
                stmt = stmt.where(Task.assigned_staff_id == staff_id)

        stmt = stmt.order_by(Task.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_visible_task(self, *, current_user: User, task_id: UUID) -> Task:
        task = self.db.get(Task, task_id)
        if task is None or task.deleted_at is not None:
            raise ValueError("Task not found")

        if current_user.role == UserRole.CA_ADMIN:
            return task

        if current_user.role == UserRole.CLIENT and task.client_id == current_user.id:
            return task

        if current_user.role == UserRole.STAFF and task.assigned_staff_id == current_user.id:
            return task

        raise PermissionError("You do not have access to this task")

    def assign_staff(self, *, ca_user: User, task_id: UUID, payload: TaskAssignRequest) -> Task:
        if ca_user.role != UserRole.CA_ADMIN:
            raise PermissionError("Only CA admin can assign tasks")

        task = self.db.get(Task, task_id)
        if task is None or task.deleted_at is not None:
            raise ValueError("Task not found")

        staff_user = self.db.get(User, payload.staff_user_id)
        if staff_user is None or staff_user.role != UserRole.STAFF or not staff_user.is_active:
            raise ValueError("Target user is not an active staff member")

        task.assigned_staff_id = staff_user.id
        if task.status == TaskStatus.TODO:
            task.status = TaskStatus.IN_PROGRESS

        self.notification_service.on_task_assigned(
            staff_id=staff_user.id,
            task_id=task.id,
            task_title=task.title,
        )

        self.db.commit()
        self.db.refresh(task)
        return task

    def update_staff_status(
        self,
        *,
        staff_user: User,
        task_id: UUID,
        payload: StaffTaskStatusUpdateRequest,
    ) -> Task:
        if staff_user.role != UserRole.STAFF:
            raise PermissionError("Only staff can update staff task status")

        task = self.db.get(Task, task_id)
        if task is None or task.deleted_at is not None:
            raise ValueError("Task not found")
        if task.assigned_staff_id != staff_user.id:
            raise PermissionError("Task is not assigned to you")

        allowed_status = {TaskStatus.IN_PROGRESS, TaskStatus.PENDING_FROM_STAFF, TaskStatus.COMPLETED_BY_STAFF}
        if payload.status not in allowed_status:
            raise ValueError("Staff can only set IN_PROGRESS, PENDING_FROM_STAFF, or COMPLETED_BY_STAFF")

        current = task.status
        if current in {TaskStatus.APPROVED_BY_CA, TaskStatus.INVOICED, TaskStatus.PAYMENT_PENDING, TaskStatus.PAYMENT_CONFIRMED, TaskStatus.DOCUMENT_RELEASED, TaskStatus.CLOSED}:
            raise ValueError("Task cannot be modified after CA approval lifecycle starts")

        task.status = payload.status

        now = datetime.now(UTC)
        if payload.status == TaskStatus.COMPLETED_BY_STAFF:
            task.staff_completed_at = now
            # Strict workflow: completed work must move to CA review queue.
            task.status = TaskStatus.UNDER_CA_REVIEW
            self.notification_service.on_task_sent_for_review(client_id=task.client_id, task_id=task.id)
        elif payload.status == TaskStatus.IN_PROGRESS:
            task.staff_completed_at = None

        self.db.commit()
        self.db.refresh(task)
        return task

    def ca_review(
        self,
        *,
        ca_user: User,
        task_id: UUID,
        payload: CAReviewRequest,
    ) -> Task:
        if ca_user.role != UserRole.CA_ADMIN:
            raise PermissionError("Only CA admin can review tasks")

        task = self.db.get(Task, task_id)
        if task is None or task.deleted_at is not None:
            raise ValueError("Task not found")
        if task.status != TaskStatus.UNDER_CA_REVIEW:
            raise ValueError("Task must be UNDER_CA_REVIEW before CA decision")

        now = datetime.now(UTC)
        task.reviewed_by_ca_id = ca_user.id
        task.ca_reviewed_at = now

        if payload.approve:
            task.status = TaskStatus.APPROVED_BY_CA
            task.approved_at = now
            decision = ApprovalDecision.APPROVED
        else:
            task.status = TaskStatus.REJECTED_BY_CA
            task.rejected_at = now
            decision = ApprovalDecision.REJECTED

        self.notification_service.on_task_reviewed(
            client_id=task.client_id,
            task_id=task.id,
            approved=payload.approve,
        )

        round_number = len(task.approvals) + 1
        approval = TaskApproval(
            task_id=task.id,
            reviewed_by_id=ca_user.id,
            round_number=round_number,
            decision=decision,
            comments=payload.comments,
        )
        self.db.add(approval)

        self.db.commit()
        self.db.refresh(task)
        return task
