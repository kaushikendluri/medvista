import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import StudyStatus


class Study(UUIDPKMixin, TimestampMixin, Base):
    """A DICOM study. Populated starting Phase 2 (DICOM ingestion)."""

    __tablename__ = "studies"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    study_uid: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    accession_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    modality: Mapped[str] = mapped_column(String(16), nullable=False)
    study_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    study_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body_part: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[StudyStatus] = mapped_column(
        Enum(StudyStatus, name="study_status"), nullable=False, default=StudyStatus.PENDING
    )
    dicom_server_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    patient: Mapped["Patient"] = relationship()  # noqa: F821
    series: Mapped[list["Series"]] = relationship(  # noqa: F821
        back_populates="study", cascade="all, delete-orphan"
    )
