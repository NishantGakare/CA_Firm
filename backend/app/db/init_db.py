from app.db.base import Base
from app.db.session import engine
from app.models import (  # noqa: F401
    AuditLog,
    Document,
    Invoice,
    Notification,
    Payment,
    RefreshToken,
    ServiceCatalog,
    Task,
    TaskApproval,
    User,
)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
