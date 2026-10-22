import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ReportStatus


class ReportCreate(BaseModel):
    study_id: uuid.UUID | None = None


class ReportUpdate(BaseModel):
    draft_content: str


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    study_id: uuid.UUID | None
    author_id: uuid.UUID | None
    author_name: str | None = None
    status: ReportStatus
    draft_content: str | None
    finalized_content: str | None
    signed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReportVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_id: uuid.UUID
    version_number: int
    author_id: uuid.UUID | None
    author_name: str | None = None
    content: str
    created_at: datetime
