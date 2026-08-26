from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.registry import AVAILABLE_MODEL_IMPLEMENTATIONS
from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.ai_model import AIModel
from app.models.enums import ModelStatus, UserRole
from app.models.user import User
from app.schemas.ai import AIModelCreate, AIModelRead
from app.services.audit import record_audit_event

router = APIRouter(prefix="/ai/models", tags=["ai"])


def _computed_status(model: AIModel) -> ModelStatus:
    """A catalog row's status is never trusted as-entered — it only reads
    AVAILABLE if the worker actually has a matching code implementation."""
    if (model.modality, model.task) in AVAILABLE_MODEL_IMPLEMENTATIONS:
        return ModelStatus.AVAILABLE
    return ModelStatus.UNAVAILABLE


def _to_read(model: AIModel) -> AIModelRead:
    return AIModelRead(**{**AIModelRead.model_validate(model).model_dump(exclude={"status"}), "status": _computed_status(model)})


@router.get("", response_model=list[AIModelRead])
def list_models(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[AIModelRead]:
    models = db.execute(select(AIModel).order_by(AIModel.modality, AIModel.name)).scalars().all()
    return [_to_read(m) for m in models]


@router.post("", response_model=AIModelRead, status_code=status.HTTP_201_CREATED)
def create_model(
    payload: AIModelCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
) -> AIModelRead:
    model = AIModel(**payload.model_dump(), status=ModelStatus.UNAVAILABLE)
    db.add(model)
    db.commit()
    db.refresh(model)

    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="ai_model.registered",
        resource_type="ai_model",
        resource_id=str(model.id),
    )
    return _to_read(model)
