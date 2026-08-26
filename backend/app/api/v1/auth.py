from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.enums import UserStatus
from app.models.user import User
from app.schemas.user import LoginRequest, LoginResponse, UserRead
from app.services.audit import record_audit_event

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account is not active")

    token = create_access_token(
        subject=str(user.id), extra_claims={"role": user.role.value, "org": str(user.organization_id)}
    )
    record_audit_event(
        db,
        user_id=user.id,
        organization_id=user.organization_id,
        action="login",
        resource_type="session",
    )
    return LoginResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)
