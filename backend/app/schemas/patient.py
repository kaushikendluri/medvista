import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import Sex


class PatientCreate(BaseModel):
    external_patient_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: Sex = Sex.UNKNOWN
    phone: str | None = None
    email: str | None = None

    @field_validator("date_of_birth")
    @classmethod
    def dob_not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return value


class PatientUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    sex: Sex | None = None
    phone: str | None = None
    email: str | None = None


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    external_patient_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: Sex
    phone: str | None
    email: str | None
    age: int


class PatientSummary(BaseModel):
    """Lighter shape used in list views and search results."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_patient_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: Sex
    age: int
