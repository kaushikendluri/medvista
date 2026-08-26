import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import StudyStatus
from app.models.imaging_instance import ImagingInstance
from app.models.series import Series
from app.models.study import Study
from app.services.dicom_metadata import InstanceMetadata


class CrossPatientStudyConflict(Exception):
    """A study UID already exists but is attached to a different patient."""


def get_or_create_study(
    db: Session, *, patient_id: uuid.UUID, metadata: InstanceMetadata
) -> Study:
    study = db.scalar(select(Study).where(Study.study_uid == metadata.study_uid))
    if study is not None:
        if study.patient_id != patient_id:
            raise CrossPatientStudyConflict(
                f"Study {metadata.study_uid} is already associated with a different patient"
            )
        return study

    study = Study(
        patient_id=patient_id,
        study_uid=metadata.study_uid,
        accession_number=metadata.accession_number,
        modality=metadata.modality,
        study_description=metadata.study_description,
        study_date=metadata.study_date,
        institution=metadata.institution,
        body_part=metadata.body_part,
        status=StudyStatus.PROCESSING,
    )
    db.add(study)
    db.flush()
    return study


def get_or_create_series(db: Session, *, study_id: uuid.UUID, metadata: InstanceMetadata) -> Series:
    series = db.scalar(select(Series).where(Series.series_uid == metadata.series_uid))
    if series is not None:
        return series

    series = Series(
        study_id=study_id,
        series_uid=metadata.series_uid,
        modality=metadata.modality,
        description=metadata.series_description,
        series_number=metadata.series_number,
        instance_count=0,
    )
    db.add(series)
    db.flush()
    return series


def register_instance(
    db: Session,
    *,
    series: Series,
    metadata: InstanceMetadata,
    storage_reference: str,
) -> tuple[ImagingInstance, bool]:
    """Returns (instance, created). If the SOP instance already exists
    (re-upload of the same file), it is returned as-is without duplicating
    the series instance count."""
    existing = db.scalar(
        select(ImagingInstance).where(ImagingInstance.sop_instance_uid == metadata.sop_instance_uid)
    )
    if existing is not None:
        return existing, False

    instance = ImagingInstance(
        series_id=series.id,
        sop_instance_uid=metadata.sop_instance_uid,
        instance_number=metadata.instance_number,
        storage_reference=storage_reference,
    )
    db.add(instance)
    series.instance_count += 1
    db.flush()
    return instance, True


def list_studies_for_patient(db: Session, *, patient_id: uuid.UUID) -> list[Study]:
    return list(
        db.execute(
            select(Study).where(Study.patient_id == patient_id).order_by(Study.study_date.desc().nullslast())
        )
        .scalars()
        .all()
    )


def get_study(db: Session, *, study_id: uuid.UUID, organization_id: uuid.UUID) -> Study | None:
    from app.models.patient import Patient

    return db.scalar(
        select(Study)
        .join(Patient, Patient.id == Study.patient_id)
        .where(Study.id == study_id, Patient.organization_id == organization_id)
    )
