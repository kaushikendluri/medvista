import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AIAnalysisStatus, AIFindingStatus, ModelStatus


class AIModelCreate(BaseModel):
    name: str
    version: str
    modality: str
    anatomy: str | None = None
    task: str
    provider: str
    model_location: str | None = None
    supported_input: str | None = None
    output_format: str | None = None


class AIModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    version: str
    modality: str
    anatomy: str | None
    task: str
    provider: str
    model_location: str | None
    supported_input: str | None
    output_format: str | None
    status: ModelStatus  # computed: only AVAILABLE if a real implementation is registered


class AIAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    study_id: uuid.UUID
    model_id: uuid.UUID | None
    model_version: str | None
    status: AIAnalysisStatus
    started_at: datetime | None
    completed_at: datetime | None
    processing_time_seconds: float | None
    error: str | None
    created_at: datetime


class AIFindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    finding_type: str
    description: str
    anatomical_region: str | None
    confidence: float | None
    severity: str | None
    status: AIFindingStatus
    coordinates: dict | None
    measurement: dict | None
    evidence_reference: str | None
    created_at: datetime


class FindingReviewRequest(BaseModel):
    status: AIFindingStatus


class PatientFindingRead(AIFindingRead):
    """A finding surfaced on the patient profile, carrying enough context
    to link back to the study/series it came from."""

    study_id: uuid.UUID
