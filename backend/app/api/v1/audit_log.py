from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import Page
from app.schemas.dashboard import ActivityItem

router = APIRouter(prefix="/audit-log", tags=["audit"])


@router.get("", response_model=Page[ActivityItem])
def list_audit_log(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN)),
    db: Session = Depends(get_db),
) -> Page[ActivityItem]:
    query = select(AuditLog, User.name).outerjoin(User, User.id == AuditLog.user_id)
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.where(AuditLog.organization_id == current_user.organization_id)

    count_query = select(func.count()).select_from(AuditLog)
    if current_user.role != UserRole.SUPER_ADMIN:
        count_query = count_query.where(AuditLog.organization_id == current_user.organization_id)
    total = db.scalar(count_query) or 0

    rows = db.execute(
        query.order_by(AuditLog.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()

    items = [
        ActivityItem(
            id=log.id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            actor_name=actor_name,
            timestamp=log.timestamp,
        )
        for log, actor_name in rows
    ]
    return Page(items=items, total=total, page=page, page_size=page_size)
