import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class ImagingInstance(UUIDPKMixin, TimestampMixin, Base):
    """A single DICOM instance (image). Populated starting Phase 2."""

    __tablename__ = "imaging_instances"

    series_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("series.id"), nullable=False, index=True
    )
    sop_instance_uid: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    instance_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_reference: Mapped[str] = mapped_column(String(512), nullable=False)

    series: Mapped["Series"] = relationship(back_populates="instances")  # noqa: F821
