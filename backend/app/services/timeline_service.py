import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.clinical_history import ClinicalHistory
from app.models.patient_event import PatientEvent
from app.models.report import Report
from app.models.study import Study
from app.schemas.dashboard import TimelineEvent


def _to_datetime(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def get_patient_timeline(db: Session, *, patient_id: uuid.UUID) -> list[TimelineEvent]:
    """Merge every event source touching this patient into one chronological
    feed. Sources with no rows yet (studies, reports before Phase 2/5) simply
    contribute nothing — no synthetic events are ever inserted."""
    events: list[TimelineEvent] = []

    history_rows = db.execute(
        select(ClinicalHistory).where(ClinicalHistory.patient_id == patient_id)
    ).scalars().all()
    for row in history_rows:
        timestamp = _to_datetime(row.onset_date) if row.onset_date else _to_datetime(row.created_at.date())
        events.append(
            TimelineEvent(
                event_type="clinical_history",
                title=row.condition,
                description=row.description,
                timestamp=timestamp,
                reference_id=row.id,
                source="clinical_history",
            )
        )

    manual_rows = db.execute(
        select(PatientEvent).where(PatientEvent.patient_id == patient_id)
    ).scalars().all()
    for row in manual_rows:
        events.append(
            TimelineEvent(
                event_type=row.event_type,
                title=row.title,
                description=row.description,
                timestamp=row.event_timestamp,
                reference_id=row.reference_id,
                source="patient_event",
            )
        )

    study_rows = db.execute(select(Study).where(Study.patient_id == patient_id)).scalars().all()
    for row in study_rows:
        timestamp = _to_datetime(row.study_date) if row.study_date else _to_datetime(row.created_at.date())
        events.append(
            TimelineEvent(
                event_type="imaging_study",
                title=row.study_description or f"{row.modality} study",
                description=f"Status: {row.status.value}",
                timestamp=timestamp,
                reference_id=row.id,
                source="study",
            )
        )

    report_rows = db.execute(select(Report).where(Report.patient_id == patient_id)).scalars().all()
    for row in report_rows:
        events.append(
            TimelineEvent(
                event_type="report",
                title="Radiology report",
                description=f"Status: {row.status.value}",
                timestamp=row.created_at,
                reference_id=row.id,
                source="report",
            )
        )

    events.sort(key=lambda e: e.timestamp, reverse=True)
    return events
