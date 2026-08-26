import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.enums import ClinicalHistoryStatus


class ClinicalHistoryCreate(BaseModel):
    condition: str
    description: str | None = None
    onset_date: date | None = None
    status: ClinicalHistoryStatus
    source: str


class ClinicalHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    condition: str
    description: str | None
    onset_date: date | None
    status: ClinicalHistoryStatus
    source: str
