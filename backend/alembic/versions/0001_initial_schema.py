"""Initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-25 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


user_role_enum = postgresql.ENUM("CA_ADMIN", "STAFF", "CLIENT", name="user_role", create_type=False)
task_status_enum = postgresql.ENUM(
    "TODO",
    "IN_PROGRESS",
    "COMPLETED_BY_STAFF",
    "PENDING_FROM_STAFF",
    "UNDER_CA_REVIEW",
    "REJECTED_BY_CA",
    "APPROVED_BY_CA",
    "INVOICED",
    "PAYMENT_PENDING",
    "PAYMENT_CONFIRMED",
    "DOCUMENT_RELEASED",
    "CLOSED",
    name="task_status",
    create_type=False,
)
approval_decision_enum = postgresql.ENUM("APPROVED", "REJECTED", name="approval_decision", create_type=False)
document_kind_enum = postgresql.ENUM(
    "CLIENT_INPUT", "STAFF_WORKING", "STAFF_OUTPUT", "FINAL_DELIVERABLE", name="document_kind", create_type=False
)
document_access_state_enum = postgresql.ENUM("LOCKED", "UNLOCKED", name="document_access_state", create_type=False)
invoice_status_enum = postgresql.ENUM(
    "DRAFT", "ISSUED", "PARTIALLY_PAID", "PAID", "VOID", "OVERDUE", name="invoice_status", create_type=False
)
payment_status_enum = postgresql.ENUM(
    "INITIATED", "SUCCEEDED", "FAILED", "REFUNDED", name="payment_status", create_type=False
)
notification_channel_enum = postgresql.ENUM("IN_APP", "EMAIL", name="notification_channel", create_type=False)
notification_status_enum = postgresql.ENUM("PENDING", "SENT", "FAILED", name="notification_status", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    user_role_enum.create(bind, checkfirst=True)
    task_status_enum.create(bind, checkfirst=True)
    approval_decision_enum.create(bind, checkfirst=True)
    document_kind_enum.create(bind, checkfirst=True)
    document_access_state_enum.create(bind, checkfirst=True)
    invoice_status_enum.create(bind, checkfirst=True)
    payment_status_enum.create(bind, checkfirst=True)
    notification_channel_enum.create(bind, checkfirst=True)
    notification_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index("ix_users_role", "users", ["role"], unique=False)
    op.create_index("ix_users_is_active", "users", ["is_active"], unique=False)

    op.create_table(
        "service_catalog",
        sa.Column("service_code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_fee", sa.Numeric(12, 2), nullable=False),
        sa.Column("sla_days", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_catalog")),
        sa.UniqueConstraint("service_code", name=op.f("uq_service_catalog_service_code")),
    )
    op.create_index("ix_service_catalog_active", "service_catalog", ["is_active"], unique=False)

    op.create_table(
        "tasks",
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_staff_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_by_ca_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", task_status_enum, server_default="TODO", nullable=False),
        sa.Column("priority", sa.String(length=20), server_default="MEDIUM", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("staff_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ca_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("document_released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"], name=op.f("fk_tasks_client_id_users"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["service_id"], ["service_catalog.id"], name=op.f("fk_tasks_service_id_service_catalog"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["assigned_staff_id"], ["users.id"], name=op.f("fk_tasks_assigned_staff_id_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_ca_id"], ["users.id"], name=op.f("fk_tasks_reviewed_by_ca_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tasks")),
    )
    op.create_index("ix_tasks_status", "tasks", ["status"], unique=False)
    op.create_index("ix_tasks_client_id", "tasks", ["client_id"], unique=False)
    op.create_index("ix_tasks_assigned_staff_id", "tasks", ["assigned_staff_id"], unique=False)
    op.create_index("ix_tasks_due_date", "tasks", ["due_date"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("issued_ip", sa.String(length=64), nullable=True),
        sa.Column("issued_user_agent", sa.String(length=400), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_refresh_tokens_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("jti", name=op.f("uq_refresh_tokens_jti")),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False)
    op.create_index("ix_refresh_tokens_jti", "refresh_tokens", ["jti"], unique=True)
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"], unique=False)

    op.create_table(
        "task_approvals",
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("round_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("decision", approval_decision_enum, nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], name=op.f("fk_task_approvals_task_id_tasks"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["reviewed_by_id"], ["users.id"], name=op.f("fk_task_approvals_reviewed_by_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_approvals")),
    )
    op.create_index("ix_task_approvals_task_id", "task_approvals", ["task_id"], unique=False)
    op.create_index("ix_task_approvals_reviewed_by_id", "task_approvals", ["reviewed_by_id"], unique=False)

    op.create_table(
        "invoices",
        sa.Column("invoice_number", sa.String(length=40), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issued_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("sub_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_due", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", invoice_status_enum, server_default="DRAFT", nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("amount_paid >= 0", name="invoice_paid_non_negative"),
        sa.CheckConstraint("total_amount >= 0", name="invoice_total_non_negative"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], name=op.f("fk_invoices_task_id_tasks"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"], name=op.f("fk_invoices_client_id_users"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["issued_by_id"], ["users.id"], name=op.f("fk_invoices_issued_by_id_users"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoices")),
        sa.UniqueConstraint("invoice_number", name=op.f("uq_invoices_invoice_number")),
        sa.UniqueConstraint("task_id", name=op.f("uq_invoices_task_id")),
    )
    op.create_index("ix_invoices_status", "invoices", ["status"], unique=False)
    op.create_index("ix_invoices_client_id", "invoices", ["client_id"], unique=False)
    op.create_index("ix_invoices_due_date", "invoices", ["due_date"], unique=False)

    op.create_table(
        "documents",
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", document_kind_enum, nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("s3_bucket", sa.String(length=120), nullable=False),
        sa.Column("s3_key", sa.String(length=1024), nullable=False),
        sa.Column("s3_version_id", sa.String(length=255), nullable=True),
        sa.Column("access_state", document_access_state_enum, server_default="LOCKED", nullable=False),
        sa.Column("approved_for_release", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_latest", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], name=op.f("fk_documents_task_id_tasks"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"], name=op.f("fk_documents_client_id_users"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"], ["users.id"], name=op.f("fk_documents_uploaded_by_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        sa.UniqueConstraint("s3_key", name=op.f("uq_documents_s3_key")),
    )
    op.create_index("ix_documents_task_id", "documents", ["task_id"], unique=False)
    op.create_index("ix_documents_client_id", "documents", ["client_id"], unique=False)
    op.create_index("ix_documents_access_state", "documents", ["access_state"], unique=False)
    op.create_index("ix_documents_is_latest", "documents", ["is_latest"], unique=False)

    op.create_table(
        "payments",
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("status", payment_status_enum, server_default="INITIATED", nullable=False),
        sa.Column("provider", sa.String(length=40), server_default="RAZORPAY", nullable=False),
        sa.Column("provider_order_id", sa.String(length=120), nullable=True),
        sa.Column("provider_payment_id", sa.String(length=120), nullable=True),
        sa.Column("provider_signature", sa.String(length=255), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount > 0", name="payment_amount_positive"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], name=op.f("fk_payments_invoice_id_invoices"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"], name=op.f("fk_payments_client_id_users"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payments")),
        sa.UniqueConstraint("provider_payment_id", name=op.f("uq_payments_provider_payment_id")),
    )
    op.create_index("ix_payments_status", "payments", ["status"], unique=False)
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"], unique=False)
    op.create_index("ix_payments_provider_payment_id", "payments", ["provider_payment_id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel", notification_channel_enum, server_default="IN_APP", nullable=False),
        sa.Column("status", notification_status_enum, server_default="PENDING", nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_notifications_user_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], name=op.f("fk_notifications_task_id_tasks"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], name=op.f("fk_notifications_invoice_id_invoices"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)
    op.create_index("ix_notifications_status", "notifications", ["status"], unique=False)
    op.create_index("ix_notifications_scheduled_for", "notifications", ["scheduled_for"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=400), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name=op.f("fk_audit_logs_actor_user_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], unique=False)
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"], unique=False)
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_entity_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_notifications_scheduled_for", table_name="notifications")
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_payments_provider_payment_id", table_name="payments")
    op.drop_index("ix_payments_invoice_id", table_name="payments")
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_table("payments")

    op.drop_index("ix_documents_is_latest", table_name="documents")
    op.drop_index("ix_documents_access_state", table_name="documents")
    op.drop_index("ix_documents_client_id", table_name="documents")
    op.drop_index("ix_documents_task_id", table_name="documents")
    op.drop_table("documents")

    op.drop_index("ix_invoices_due_date", table_name="invoices")
    op.drop_index("ix_invoices_client_id", table_name="invoices")
    op.drop_index("ix_invoices_status", table_name="invoices")
    op.drop_table("invoices")

    op.drop_index("ix_task_approvals_reviewed_by_id", table_name="task_approvals")
    op.drop_index("ix_task_approvals_task_id", table_name="task_approvals")
    op.drop_table("task_approvals")

    op.drop_index("ix_refresh_tokens_expires_at", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_jti", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index("ix_tasks_due_date", table_name="tasks")
    op.drop_index("ix_tasks_assigned_staff_id", table_name="tasks")
    op.drop_index("ix_tasks_client_id", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_table("tasks")

    op.drop_index("ix_service_catalog_active", table_name="service_catalog")
    op.drop_table("service_catalog")

    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    notification_status_enum.drop(bind, checkfirst=True)
    notification_channel_enum.drop(bind, checkfirst=True)
    payment_status_enum.drop(bind, checkfirst=True)
    invoice_status_enum.drop(bind, checkfirst=True)
    document_access_state_enum.drop(bind, checkfirst=True)
    document_kind_enum.drop(bind, checkfirst=True)
    approval_decision_enum.drop(bind, checkfirst=True)
    task_status_enum.drop(bind, checkfirst=True)
    user_role_enum.drop(bind, checkfirst=True)
