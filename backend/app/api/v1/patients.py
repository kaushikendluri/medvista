import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.clinical_history import ClinicalHistory
from app.models.enums import UserRole
from app.models.patient import Patient
from app.models.user import User
from app.schemas.clinical_history import ClinicalHistoryCreate, ClinicalHistoryRead
from app.schemas.common import Page
from app.schemas.dashboard import TimelineEvent
from app.schemas.patient import PatientCreate, PatientRead, PatientSummary, PatientUpdate
from app.services.audit import record_audit_event
from app.services.patient_service import calculate_age, get_patient, list_patients
from app.services.timeline_service import get_patient_timeline

router = APIRouter(prefix="/patients", tags=["patients"])

CLINICAL_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.HOSPITAL_ADMIN,
    UserRole.DOCTOR,
    UserRole.RADIOLOGIST,
    UserRole.TECHNICIAN,
)


def _to_read(patient: Patient) -> PatientRead:
    return PatientRead(
        id=patient.id,
        organization_id=patient.organization_id,
        external_patient_id=patient.external_patient_id,
        first_name=patient.first_name,
        last_name=patient.last_name,
        date_of_birth=patient.date_of_birth,
        sex=patient.sex,
        phone=patient.phone,
        email=patient.email,
        age=calculate_age(patient.date_of_birth),
    )


def _to_summary(patient: Patient) -> PatientSummary:
    return PatientSummary(
        id=patient.id,
        external_patient_id=patient.external_patient_id,
        first_name=patient.first_name,
        last_name=patient.last_name,
        date_of_birth=patient.date_of_birth,
        sex=patient.sex,
        age=calculate_age(patient.date_of_birth),
    )


@router.get("", response_model=Page[PatientSummary])
def list_patients_endpoint(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    current_user: User = Depends(require_roles(*CLINICAL_ROLES)),
    db: Session = Depends(get_db),
) -> Page[PatientSummary]:
    items, total = list_patients(
        db,
        organization_id=current_user.organization_id,
        search=search,
        page=page,
        page_size=page_size,
    )
    return Page(items=[_to_summary(p) for p in items], total=total, page=page, page_size=page_size)


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    current_user: User = Depends(
        require_roles(UserRole.HOSPITAL_ADMIN, UserRole.DOCTOR, UserRole.TECHNICIAN, UserRole.RADIOLOGIST)
    ),
    db: Session = Depends(get_db),
) -> PatientRead:
    patient = Patient(organization_id=current_user.organization_id, **payload.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)

    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="patient.created",
        resource_type="patient",
        resource_id=str(patient.id),
    )
    return _to_read(patient)


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient_endpoint(
    patient_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CLINICAL_ROLES)),
    db: Session = Depends(get_db),
) -> PatientRead:
    patient = get_patient(db, patient_id=patient_id, organization_id=current_user.organization_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Patient not found")

    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="patient.viewed",
        resource_type="patient",
        resource_id=str(patient.id),
    )
    return _to_read(patient)


@router.patch("/{patient_id}", response_model=PatientRead)
def update_patient(
    patient_id: uuid.UUID,
    payload: PatientUpdate,
    current_user: User = Depends(
        require_roles(UserRole.HOSPITAL_ADMIN, UserRole.DOCTOR, UserRole.TECHNICIAN, UserRole.RADIOLOGIST)
    ),
    db: Session = Depends(get_db),
) -> PatientRead:
    patient = get_patient(db, patient_id=patient_id, organization_id=current_user.organization_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Patient not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)

    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="patient.updated",
        resource_type="patient",
        resource_id=str(patient.id),
    )
    return _to_read(patient)


@router.get("/{patient_id}/timeline", response_model=list[TimelineEvent])
def patient_timeline(
    patient_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CLINICAL_ROLES)),
    db: Session = Depends(get_db),
) -> list[TimelineEvent]:
    patient = get_patient(db, patient_id=patient_id, organization_id=current_user.organization_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return get_patient_timeline(db, patient_id=patient_id)


@router.get("/{patient_id}/clinical-history", response_model=list[ClinicalHistoryRead])
def list_clinical_history(
    patient_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CLINICAL_ROLES)),
    db: Session = Depends(get_db),
) -> list[ClinicalHistoryRead]:
    patient = get_patient(db, patient_id=patient_id, organization_id=current_user.organization_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Patient not found")
    rows = (
        db.query(ClinicalHistory)
        .filter(ClinicalHistory.patient_id == patient_id)
        .order_by(ClinicalHistory.onset_date.desc().nullslast())
        .all()
    )
    return [ClinicalHistoryRead.model_validate(r) for r in rows]


@router.post(
    "/{patient_id}/clinical-history",
    response_model=ClinicalHistoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_clinical_history(
    patient_id: uuid.UUID,
    payload: ClinicalHistoryCreate,
    current_user: User = Depends(
        require_roles(UserRole.HOSPITAL_ADMIN, UserRole.DOCTOR, UserRole.RADIOLOGIST)
    ),
    db: Session = Depends(get_db),
) -> ClinicalHistoryRead:
    patient = get_patient(db, patient_id=patient_id, organization_id=current_user.organization_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Patient not found")

    entry = ClinicalHistory(patient_id=patient_id, **payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)

    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="clinical_history.created",
        resource_type="clinical_history",
        resource_id=str(entry.id),
    )
    return ClinicalHistoryRead.model_validate(entry)
