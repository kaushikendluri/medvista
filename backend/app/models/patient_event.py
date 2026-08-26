import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class PatientEvent(UUIDPKMixin, TimestampMixin, Base):
    """A single node in the longitudinal patient timeline.

    Rows are created here for event types that have no dedicated table of
    their own (e.g. appointments, free-text notes); events derived from
    imaging/labs/reports/AI analyses are read directly from their source
    tables and merged at query time rather than duplicated here.
    """

    __tablename__ = "patient_events"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    patient: Mapped["Patient"] = relationship(back_populates="events")  # noqa: F821
