import io
import uuid
import zipfile
from collections.abc import Iterator

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.enums import StudyStatus, UserRole
from app.models.imaging_instance import ImagingInstance
from app.models.series import Series
from app.models.study import Study
from app.models.user import User
from app.schemas.study import InstanceRead, SeriesRead, StudyDetail, StudyRead, UploadFailure, UploadResult
from app.services.audit import record_audit_event
from app.services.dicom_metadata import InvalidDicomFile, extract_metadata
from app.services.orthanc_client import OrthancError
from app.services import orthanc_client
from app.services.patient_service import get_patient
from app.services.study_service import (
    CrossPatientStudyConflict,
    get_or_create_series,
    get_or_create_study,
    get_study,
    list_studies_for_patient,
    register_instance,
)

router = APIRouter(tags=["studies"])

CLINICAL_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.HOSPITAL_ADMIN,
    UserRole.DOCTOR,
    UserRole.RADIOLOGIST,
    UserRole.TECHNICIAN,
)

MAX_FILES_PER_UPLOAD = 500
MAX_TOTAL_BYTES = 500 * 1024 * 1024  # 500MB per upload request


def _iter_uploaded_blobs(files: list[UploadFile]) -> Iterator[tuple[str, bytes]]:
    """Yields (filename, bytes) for every DICOM candidate in the upload,
    transparently expanding any .zip archives."""
    for upload in files:
        filename = upload.filename or "unnamed"
        data = upload.file.read()
        if filename.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    for member in archive.infolist():
                        if member.is_dir():
                            continue
                        yield f"{filename}:{member.filename}", archive.read(member)
            except zipfile.BadZipFile:
                yield filename, data  # let downstream validation reject it clearly
        else:
            yield filename, data


@router.post(
    "/patients/{patient_id}/studies/upload",
    response_model=UploadResult,
    status_code=status.HTTP_201_CREATED,
)
def upload_study(
    patient_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(require_roles(*CLINICAL_ROLES)),
    db: Session = Depends(get_db),
) -> UploadResult:
    patient = get_patient(db, patient_id=patient_id, organization_id=current_user.organization_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Patient not found")
    if not files:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No files were uploaded")
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=f"Too many files (max {MAX_FILES_PER_UPLOAD})"
        )
    if not orthanc_client.is_available():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The DICOM server is currently unavailable. Please try again later.",
        )

    failures: list[UploadFailure] = []
    instances_created = 0
    instances_already_present = 0
    touched_study_ids: set[uuid.UUID] = set()
    total_bytes = 0
    files_received = 0

    for filename, blob in _iter_uploaded_blobs(files):
        files_received += 1
        total_bytes += len(blob)
        if total_bytes > MAX_TOTAL_BYTES:
            failures.append(
                UploadFailure(filename=filename, reason="Upload exceeds the 500MB request limit")
            )
            break

        try:
            metadata = extract_metadata(blob, filename)
        except InvalidDicomFile as exc:
            failures.append(UploadFailure(filename=filename, reason=str(exc)))
            continue

        try:
            with db.begin_nested():
                study = get_or_create_study(db, patient_id=patient_id, metadata=metadata)
                orthanc_result = orthanc_client.upload_instance(blob)
                series = get_or_create_series(db, study_id=study.id, metadata=metadata)
                _, created = register_instance(
                    db,
                    series=series,
                    metadata=metadata,
                    storage_reference=orthanc_result["ID"],
                )
                study.dicom_server_reference = orthanc_result.get("ParentStudy")
                study.status = StudyStatus.READY
            db.commit()
        except (CrossPatientStudyConflict, OrthancError) as exc:
            failures.append(UploadFailure(filename=filename, reason=str(exc)))
            continue

        touched_study_ids.add(study.id)
        if created:
            instances_created += 1
        else:
            instances_already_present += 1

    study_id = next(iter(touched_study_ids), None)
    final_study = db.get(Study, study_id) if study_id else None

    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="study.uploaded",
        resource_type="study",
        resource_id=str(study_id) if study_id else None,
        meta={
            "patient_id": str(patient_id),
            "files_received": files_received,
            "instances_created": instances_created,
            "failures": len(failures),
        },
    )

    return UploadResult(
        study_id=study_id,
        files_received=files_received,
        instances_created=instances_created,
        instances_already_present=instances_already_present,
        failures=failures,
        status=final_study.status if final_study else None,
    )


@router.get("/patients/{patient_id}/studies", response_model=list[StudyRead])
def list_patient_studies(
    patient_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CLINICAL_ROLES)),
    db: Session = Depends(get_db),
) -> list[StudyRead]:
    patient = get_patient(db, patient_id=patient_id, organization_id=current_user.organization_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return [StudyRead.model_validate(s) for s in list_studies_for_patient(db, patient_id=patient_id)]


@router.get("/studies/{study_id}", response_model=StudyDetail)
def get_study_detail(
    study_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CLINICAL_ROLES)),
    db: Session = Depends(get_db),
) -> StudyDetail:
    study = get_study(db, study_id=study_id, organization_id=current_user.organization_id)
    if study is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Study not found")

    series = db.execute(
        select(Series).where(Series.study_id == study.id).order_by(Series.series_number)
    ).scalars().all()

    record_audit_event(
        db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="study.viewed",
        resource_type="study",
        resource_id=str(study.id),
    )

    return StudyDetail(
        **StudyRead.model_validate(study).model_dump(),
        series=[SeriesRead.model_validate(s) for s in series],
    )


@router.get("/studies/{study_id}/series/{series_id}/instances", response_model=list[InstanceRead])
def list_series_instances(
    study_id: uuid.UUID,
    series_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CLINICAL_ROLES)),
    db: Session = Depends(get_db),
) -> list[InstanceRead]:
    study = get_study(db, study_id=study_id, organization_id=current_user.organization_id)
    if study is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Study not found")

    series = db.scalar(select(Series).where(Series.id == series_id, Series.study_id == study_id))
    if series is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Series not found")

    instances = db.execute(
        select(ImagingInstance)
        .where(ImagingInstance.series_id == series_id)
        .order_by(ImagingInstance.instance_number)
    ).scalars().all()
    return [InstanceRead.model_validate(i) for i in instances]


def _resolve_instance(db: Session, *, study_id: uuid.UUID, instance_id: uuid.UUID) -> ImagingInstance:
    instance = db.scalar(
        select(ImagingInstance)
        .join(Series, Series.id == ImagingInstance.series_id)
        .where(ImagingInstance.id == instance_id, Series.study_id == study_id)
    )
    if instance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Instance not found")
    return instance


@router.get("/studies/{study_id}/instances/{instance_id}/preview")
def get_instance_preview(
    study_id: uuid.UUID,
    instance_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CLINICAL_ROLES)),
    db: Session = Depends(get_db),
) -> Response:
    study = get_study(db, study_id=study_id, organization_id=current_user.organization_id)
    if study is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Study not found")
    instance = _resolve_instance(db, study_id=study_id, instance_id=instance_id)

    try:
        data, content_type = orthanc_client.fetch_instance_preview(instance.storage_reference)
    except OrthancError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from None

    return Response(content=data, media_type=content_type)


@router.get("/studies/{study_id}/instances/{instance_id}/file")
def get_instance_file(
    study_id: uuid.UUID,
    instance_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CLINICAL_ROLES)),
    db: Session = Depends(get_db),
) -> Response:
    """The raw DICOM Part 10 file, used by the frontend's Cornerstone3D
    wadouri image loader to parse and render actual pixel data client-side."""
    study = get_study(db, study_id=study_id, organization_id=current_user.organization_id)
    if study is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Study not found")
    instance = _resolve_instance(db, study_id=study_id, instance_id=instance_id)

    try:
        data, content_type = orthanc_client.fetch_instance_file(instance.storage_reference)
    except OrthancError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from None

    return Response(content=data, media_type=content_type)
