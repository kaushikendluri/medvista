import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.annotation import Annotation
from app.models.enums import UserRole
from app.models.measurement import Measurement
from app.models.user import User
from app.schemas.annotation import (
    AnnotationCreate,
    AnnotationRead,
    MeasurementCreate,
    MeasurementRead,
)
from app.services.audit import record_audit_event
from app.services.study_service import get_study

router = APIRouter(tags=["imaging-review"])

REVIEW_ROLES = (UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.DOCTOR, UserRole.RADIOLOGIST)
VIEW_ROLES = REVIEW_ROLES + (UserRole.TECHNICIAN,)


def _require_study(db: Session, study_id: uuid.UUID, org_id: uuid.UUID):
    study = get_study(db, study_id=study_id, organization_id=org_id)
    if study is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Study not found")
    return study


def _can_modify(user: User, owner_id: uuid.UUID) -> bool:
    return user.id == owner_id or user.role in (UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN)


# --- Annotations ---------------------------------------------------------


@router.get("/studies/{study_id}/annotations", response_model=list[AnnotationRead])
def list_annotations(
    study_id: uuid.UUID,
    current_user: User = Depends(require_roles(*VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> list[AnnotationRead]:
    _require_study(db, study_id, current_user.organization_id)
    rows = db.execute(
        select(Annotation, User.name)
        .outerjoin(User, User.id == Annotation.user_id)
        .where(Annotation.study_id == study_id)
        .order_by(Annotation.created_at)
    ).all()
    return [
        AnnotationRead(**AnnotationRead.model_validate(a).model_dump(exclude={"author_name"}), author_name=name)
        for a, name in rows
    ]


@router.post("/studies/{study_id}/annotations", response_model=AnnotationRead, status_code=status.HTTP_201_CREATED)
def create_annotation(
    study_id: uuid.UUID,
    payload: AnnotationCreate,
    current_user: User = Depends(require_roles(*REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> AnnotationRead:
    _require_study(db, study_id, current_user.organization_id)
    annotation = Annotation(study_id=study_id, user_id=current_user.id, **payload.model_dump())
    db.add(annotation)
    db.commit()
    db.refresh(annotation)

    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="annotation.created",
        resource_type="annotation",
        resource_id=str(annotation.id),
        meta={"study_id": str(study_id)},
    )
    return AnnotationRead(
        **AnnotationRead.model_validate(annotation).model_dump(exclude={"author_name"}),
        author_name=current_user.name,
    )


@router.delete("/annotations/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_annotation(
    annotation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    annotation = db.get(Annotation, annotation_id)
    if annotation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Annotation not found")
    study = get_study(db, study_id=annotation.study_id, organization_id=current_user.organization_id)
    if study is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Annotation not found")
    if not _can_modify(current_user, annotation.user_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="You can only delete your own annotations")

    db.delete(annotation)
    db.commit()
    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="annotation.deleted",
        resource_type="annotation",
        resource_id=str(annotation_id),
    )


# --- Measurements ----------------------------------------------------------


@router.get("/studies/{study_id}/measurements", response_model=list[MeasurementRead])
def list_measurements(
    study_id: uuid.UUID,
    current_user: User = Depends(require_roles(*VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> list[MeasurementRead]:
    _require_study(db, study_id, current_user.organization_id)
    rows = db.execute(
        select(Measurement, User.name)
        .outerjoin(User, User.id == Measurement.user_id)
        .where(Measurement.study_id == study_id)
        .order_by(Measurement.created_at)
    ).all()
    return [
        MeasurementRead(**MeasurementRead.model_validate(m).model_dump(exclude={"author_name"}), author_name=name)
        for m, name in rows
    ]


@router.post("/studies/{study_id}/measurements", response_model=MeasurementRead, status_code=status.HTTP_201_CREATED)
def create_measurement(
    study_id: uuid.UUID,
    payload: MeasurementCreate,
    current_user: User = Depends(require_roles(*REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> MeasurementRead:
    _require_study(db, study_id, current_user.organization_id)
    measurement = Measurement(
        study_id=study_id, user_id=current_user.id, source="physician", **payload.model_dump()
    )
    db.add(measurement)
    db.commit()
    db.refresh(measurement)

    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="measurement.created",
        resource_type="measurement",
        resource_id=str(measurement.id),
        meta={"study_id": str(study_id), "value": measurement.value, "unit": measurement.unit},
    )
    return MeasurementRead(
        **MeasurementRead.model_validate(measurement).model_dump(exclude={"author_name"}),
        author_name=current_user.name,
    )


@router.delete("/measurements/{measurement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_measurement(
    measurement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    measurement = db.get(Measurement, measurement_id)
    if measurement is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Measurement not found")
    study = get_study(db, study_id=measurement.study_id, organization_id=current_user.organization_id)
    if study is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Measurement not found")
    if not _can_modify(current_user, measurement.user_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="You can only delete your own measurements")

    db.delete(measurement)
    db.commit()
    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="measurement.deleted",
        resource_type="measurement",
        resource_id=str(measurement_id),
    )
