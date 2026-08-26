import uuid

from pydantic import BaseModel, ConfigDict

from app.models.enums import OrganizationType


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: OrganizationType
