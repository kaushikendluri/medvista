import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import Sex


class Patient(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "patients"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    external_patient_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    sex: Mapped[Sex] = mapped_column(Enum(Sex, name="patient_sex"), nullable=False, default=Sex.UNKNOWN)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="patients")  # noqa: F821
    clinical_history: Mapped[list["ClinicalHistory"]] = relationship(  # noqa: F821
        back_populates="patient", cascade="all, delete-orphan"
    )
    events: Mapped[list["PatientEvent"]] = relationship(  # noqa: F821
        back_populates="patient", cascade="all, delete-orphan"
    )
