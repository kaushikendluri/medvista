import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import AIAnalysisStatus


class AIAnalysis(UUIDPKMixin, TimestampMixin, Base):
    """A single AI inference job run against a study. Populated starting Phase 4."""

    __tablename__ = "ai_analyses"

    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studies.id"), nullable=False, index=True
    )
    model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_models.id"), nullable=True
    )
    model_version: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[AIAnalysisStatus] = mapped_column(
        Enum(AIAnalysisStatus, name="ai_analysis_status"),
        nullable=False,
        default=AIAnalysisStatus.QUEUED,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    findings: Mapped[list["AIFinding"]] = relationship(  # noqa: F821
        back_populates="analysis", cascade="all, delete-orphan"
    )
