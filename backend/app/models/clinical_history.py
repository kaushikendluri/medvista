import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import ClinicalHistoryStatus


class ClinicalHistory(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "clinical_history"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    condition: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    onset_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[ClinicalHistoryStatus] = mapped_column(
        Enum(ClinicalHistoryStatus, name="clinical_history_status"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(255), nullable=False)

    patient: Mapped["Patient"] = relationship(back_populates="clinical_history")  # noqa: F821
