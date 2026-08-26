from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserCreate, UserRead
from app.services.audit import record_audit_event

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN)),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    query = select(User)
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.where(User.organization_id == current_user.organization_id)
    users = db.execute(query.order_by(User.name)).scalars().all()
    return [UserRead.model_validate(u) for u in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN)),
    db: Session = Depends(get_db),
) -> UserRead:
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="A user with this email already exists")
    if payload.role == UserRole.SUPER_ADMIN and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only a super admin can create super admins")

    user = User(
        organization_id=current_user.organization_id,
        role=payload.role,
        name=payload.name,
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="user.created",
        resource_type="user",
        resource_id=str(user.id),
    )
    return UserRead.model_validate(user)
