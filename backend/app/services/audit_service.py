"""审计日志服务。"""
from sqlalchemy.orm import Session

from app.models import User
from app.models.rbac import AuditLog


def write_audit(
    db: Session,
    *,
    actor: User | None,
    action: str,
    target_type: str,
    target_id: str,
    detail: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor.id if actor else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
    )
