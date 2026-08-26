import uuid

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import AIFindingStatus


class AIFinding(UUIDPKMixin, TimestampMixin, Base):
    """A single AI-generated observation. Populated starting Phase 4."""

    __tablename__ = "ai_findings"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_analyses.id"), nullable=False, index=True
    )
    finding_type: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    anatomical_region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[AIFindingStatus] = mapped_column(
        Enum(AIFindingStatus, name="ai_finding_status"),
        nullable=False,
        default=AIFindingStatus.AI_FLAGGED,
    )
    coordinates: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    measurement: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evidence_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)

    analysis: Mapped["AIAnalysis"] = relationship(back_populates="findings")  # noqa: F821
