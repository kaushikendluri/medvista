import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class Series(UUIDPKMixin, TimestampMixin, Base):
    """A DICOM series within a study. Populated starting Phase 2."""

    __tablename__ = "series"

    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studies.id"), nullable=False, index=True
    )
    series_uid: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    modality: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    series_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    instance_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    study: Mapped["Study"] = relationship(back_populates="series")  # noqa: F821
    instances: Mapped[list["ImagingInstance"]] = relationship(  # noqa: F821
        back_populates="series", cascade="all, delete-orphan"
    )
