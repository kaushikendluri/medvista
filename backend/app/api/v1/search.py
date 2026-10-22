from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.patient import Patient
from app.models.report import Report
from app.models.study import Study
from app.models.user import User
from app.schemas.search import SearchResponse, SearchResultItem
from app.services.patient_service import calculate_age

router = APIRouter(tags=["search"])

RESULTS_PER_CATEGORY = 5


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(min_length=2),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchResponse:
    org_id = current_user.organization_id
    pattern = f"%{q.strip()}%"
    results: list[SearchResultItem] = []

    if current_user.role != UserRole.RESEARCHER:
        patients = db.execute(
            select(Patient)
            .where(
                Patient.organization_id == org_id,
                or_(
                    Patient.first_name.ilike(pattern),
                    Patient.last_name.ilike(pattern),
                    Patient.external_patient_id.ilike(pattern),
                ),
            )
            .limit(RESULTS_PER_CATEGORY)
        ).scalars().all()
        for p in patients:
            results.append(
                SearchResultItem(
                    type="patient",
                    id=str(p.id),
                    title=f"{p.first_name} {p.last_name}",
                    subtitle=f"ID {p.external_patient_id} · {calculate_age(p.date_of_birth)} yrs",
                    href=f"/patients/{p.id}",
                )
            )

        studies = db.execute(
            select(Study, Patient)
            .join(Patient, Patient.id == Study.patient_id)
            .where(
                Patient.organization_id == org_id,
                or_(
                    Study.study_description.ilike(pattern),
                    Study.modality.ilike(pattern),
                    Study.body_part.ilike(pattern),
                ),
            )
            .limit(RESULTS_PER_CATEGORY)
        ).all()
        for study, patient in studies:
            results.append(
                SearchResultItem(
                    type="study",
                    id=str(study.id),
                    title=study.study_description or f"{study.modality} study",
                    subtitle=f"{patient.first_name} {patient.last_name}",
                    href=f"/patients/{patient.id}/studies/{study.id}",
                )
            )

        reports = db.execute(
            select(Report, Patient)
            .join(Patient, Patient.id == Report.patient_id)
            .where(
                Patient.organization_id == org_id,
                or_(Patient.first_name.ilike(pattern), Patient.last_name.ilike(pattern)),
            )
            .limit(RESULTS_PER_CATEGORY)
        ).all()
        for report, patient in reports:
            results.append(
                SearchResultItem(
                    type="report",
                    id=str(report.id),
                    title=f"Report — {patient.first_name} {patient.last_name}",
                    subtitle=report.status.value,
                    href=f"/patients/{patient.id}/reports/{report.id}",
                )
            )

    if current_user.role in (UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN):
        users = db.execute(
            select(User)
            .where(
                User.organization_id == org_id,
                or_(User.name.ilike(pattern), User.email.ilike(pattern)),
            )
            .limit(RESULTS_PER_CATEGORY)
        ).scalars().all()
        for u in users:
            results.append(
                SearchResultItem(
                    type="user",
                    id=str(u.id),
                    title=u.name,
                    subtitle=f"{u.role.value.replace('_', ' ')} · {u.email}",
                    href="/admin/users",
                )
            )

    return SearchResponse(query=q, results=results)
