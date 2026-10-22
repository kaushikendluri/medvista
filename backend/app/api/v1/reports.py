import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.enums import ReportStatus, UserRole
from app.models.report import Report
from app.models.report_version import ReportVersion
from app.models.user import User
from app.schemas.report import ReportCreate, ReportRead, ReportUpdate, ReportVersionRead
from app.services.audit import record_audit_event
from app.services.patient_service import get_patient
from app.services.report_service import build_draft_template
from app.services.study_service import get_study

router = APIRouter(tags=["reports"])

REVIEW_ROLES = (UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.DOCTOR, UserRole.RADIOLOGIST)
VIEW_ROLES = REVIEW_ROLES + (UserRole.TECHNICIAN,)


def _to_read(report: Report, author_name: str | None) -> ReportRead:
    return ReportRead(**ReportRead.model_validate(report).model_dump(exclude={"author_name"}), author_name=author_name)


def _get_report_or_404(db: Session, report_id: uuid.UUID, org_id: uuid.UUID) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found")
    patient = get_patient(db, patient_id=report.patient_id, organization_id=org_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.post("/patients/{patient_id}/reports", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
def create_report(
    patient_id: uuid.UUID,
    payload: ReportCreate,
    current_user: User = Depends(require_roles(*REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> ReportRead:
    patient = get_patient(db, patient_id=patient_id, organization_id=current_user.organization_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Patient not found")

    study = None
    if payload.study_id is not None:
        study = get_study(db, study_id=payload.study_id, organization_id=current_user.organization_id)
        if study is None or study.patient_id != patient_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Study not found for this patient")

    draft = build_draft_template(db, patient=patient, study=study)
    report = Report(
        patient_id=patient_id,
        study_id=payload.study_id,
        author_id=current_user.id,
        status=ReportStatus.PHYSICIAN_DRAFT,
        draft_content=draft,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="report.created",
        resource_type="report",
        resource_id=str(report.id),
    )
    return _to_read(report, current_user.name)


@router.get("/patients/{patient_id}/reports", response_model=list[ReportRead])
def list_patient_reports(
    patient_id: uuid.UUID,
    current_user: User = Depends(require_roles(*VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> list[ReportRead]:
    patient = get_patient(db, patient_id=patient_id, organization_id=current_user.organization_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Patient not found")
    rows = db.execute(
        select(Report, User.name)
        .outerjoin(User, User.id == Report.author_id)
        .where(Report.patient_id == patient_id)
        .order_by(Report.created_at.desc())
    ).all()
    return [_to_read(r, name) for r, name in rows]


@router.get("/reports/{report_id}", response_model=ReportRead)
def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(require_roles(*VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> ReportRead:
    report = _get_report_or_404(db, report_id, current_user.organization_id)
    author_name = db.get(User, report.author_id).name if report.author_id else None
    return _to_read(report, author_name)


@router.patch("/reports/{report_id}", response_model=ReportRead)
def update_report(
    report_id: uuid.UUID,
    payload: ReportUpdate,
    current_user: User = Depends(require_roles(*REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> ReportRead:
    report = _get_report_or_404(db, report_id, current_user.organization_id)
    if report.status in (ReportStatus.FINALIZED, ReportStatus.SIGNED):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="A finalized or signed report cannot be edited")

    existing_versions = db.execute(
        select(ReportVersion).where(ReportVersion.report_id == report.id)
    ).scalars().all()
    version = ReportVersion(
        report_id=report.id,
        version_number=len(existing_versions) + 1,
        author_id=current_user.id,
        content=report.draft_content or "",
    )
    db.add(version)

    report.draft_content = payload.draft_content
    db.commit()
    db.refresh(report)

    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="report.edited",
        resource_type="report",
        resource_id=str(report.id),
    )
    return _to_read(report, current_user.name)


@router.get("/reports/{report_id}/versions", response_model=list[ReportVersionRead])
def list_report_versions(
    report_id: uuid.UUID,
    current_user: User = Depends(require_roles(*VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> list[ReportVersionRead]:
    _get_report_or_404(db, report_id, current_user.organization_id)
    rows = db.execute(
        select(ReportVersion, User.name)
        .outerjoin(User, User.id == ReportVersion.author_id)
        .where(ReportVersion.report_id == report_id)
        .order_by(ReportVersion.version_number)
    ).all()
    return [
        ReportVersionRead(**ReportVersionRead.model_validate(v).model_dump(exclude={"author_name"}), author_name=name)
        for v, name in rows
    ]


@router.post("/reports/{report_id}/finalize", response_model=ReportRead)
def finalize_report(
    report_id: uuid.UUID,
    current_user: User = Depends(require_roles(*REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> ReportRead:
    report = _get_report_or_404(db, report_id, current_user.organization_id)
    if report.status != ReportStatus.PHYSICIAN_DRAFT:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Only a draft report can be finalized")

    report.status = ReportStatus.FINALIZED
    report.finalized_content = report.draft_content
    db.commit()
    db.refresh(report)

    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="report.finalized",
        resource_type="report",
        resource_id=str(report.id),
    )
    return _to_read(report, current_user.name)


@router.post("/reports/{report_id}/sign", response_model=ReportRead)
def sign_report(
    report_id: uuid.UUID,
    current_user: User = Depends(require_roles(*REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> ReportRead:
    """Signing is restricted to the report's own author — it represents a
    personal clinical attestation, not something even an admin can do on a
    physician's behalf."""
    report = _get_report_or_404(db, report_id, current_user.organization_id)
    if report.status != ReportStatus.FINALIZED:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Only a finalized report can be signed")
    if report.author_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only the report's author can sign it")

    report.status = ReportStatus.SIGNED
    report.signed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)

    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="report.signed",
        resource_type="report",
        resource_id=str(report.id),
    )
    return _to_read(report, current_user.name)
