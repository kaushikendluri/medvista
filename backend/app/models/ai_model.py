from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import ModelStatus


class AIModel(UUIDPKMixin, TimestampMixin, Base):
    """Registry entry for an imaging AI model. Populated starting Phase 4."""

    __tablename__ = "ai_models"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    modality: Mapped[str] = mapped_column(String(16), nullable=False)
    anatomy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    model_location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[ModelStatus] = mapped_column(
        Enum(ModelStatus, name="model_status"), nullable=False, default=ModelStatus.UNAVAILABLE
    )
    supported_input: Mapped[str | None] = mapped_column(String(255), nullable=True)
    output_format: Mapped[str | None] = mapped_column(String(120), nullable=True)
