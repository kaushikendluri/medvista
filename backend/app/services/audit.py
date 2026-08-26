import uuid

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record_audit_event(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    organization_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    meta: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        organization_id=organization_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        meta=meta,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
