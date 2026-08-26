import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.patient import Patient


def calculate_age(date_of_birth: date, as_of: date | None = None) -> int:
    as_of = as_of or date.today()
    years = as_of.year - date_of_birth.year
    had_birthday = (as_of.month, as_of.day) >= (date_of_birth.month, date_of_birth.day)
    return years if had_birthday else years - 1


def list_patients(
    db: Session,
    *,
    organization_id: uuid.UUID,
    search: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Patient], int]:
    query = select(Patient).where(Patient.organization_id == organization_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Patient.first_name.ilike(pattern),
                Patient.last_name.ilike(pattern),
                Patient.external_patient_id.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = (
        db.execute(
            query.order_by(Patient.last_name, Patient.first_name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return list(items), total


def get_patient(db: Session, *, patient_id: uuid.UUID, organization_id: uuid.UUID) -> Patient | None:
    return db.scalar(
        select(Patient).where(
            Patient.id == patient_id, Patient.organization_id == organization_id
        )
    )
