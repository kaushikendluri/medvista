import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnnotationCreate(BaseModel):
    series_id: uuid.UUID | None = None
    type: str
    geometry: dict
    label: str | None = None
    meta: dict | None = None


class AnnotationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    study_id: uuid.UUID
    series_id: uuid.UUID | None
    user_id: uuid.UUID
    author_name: str | None = None
    type: str
    geometry: dict
    label: str | None
    meta: dict | None
    created_at: datetime


class MeasurementCreate(BaseModel):
    series_id: uuid.UUID | None = None
    type: str
    value: float
    unit: str
    geometry: dict


class MeasurementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    study_id: uuid.UUID
    series_id: uuid.UUID | None
    user_id: uuid.UUID | None
    author_name: str | None = None
    type: str
    value: float
    unit: str
    geometry: dict
    source: str
    created_at: datetime
