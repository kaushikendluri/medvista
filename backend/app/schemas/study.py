import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.enums import StudyStatus


class SeriesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    series_uid: str
    modality: str
    description: str | None
    series_number: int | None
    instance_count: int


class InstanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sop_instance_uid: str
    instance_number: int | None


class StudyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    study_uid: str
    accession_number: str | None
    modality: str
    study_description: str | None
    study_date: date | None
    institution: str | None
    body_part: str | None
    status: StudyStatus


class StudyDetail(StudyRead):
    series: list[SeriesRead]


class UploadFailure(BaseModel):
    filename: str
    reason: str


class UploadResult(BaseModel):
    study_id: uuid.UUID | None
    files_received: int
    instances_created: int
    instances_already_present: int
    failures: list[UploadFailure]
    status: StudyStatus | None
