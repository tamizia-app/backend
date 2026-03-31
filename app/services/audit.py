from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


def create_audit_log(
    db: Session,
    *,
    user: User | None,
    action: str,
    entity_type: str,
    entity_id: UUID | str | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    audit = AuditLog(
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        metadata_json=metadata,
    )
    db.add(audit)
    db.flush()
    return audit
