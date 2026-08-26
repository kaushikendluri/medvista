from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import OrganizationType


class Organization(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[OrganizationType] = mapped_column(
        Enum(OrganizationType, name="organization_type"), nullable=False
    )

    users: Mapped[list["User"]] = relationship(back_populates="organization")  # noqa: F821
    patients: Mapped[list["Patient"]] = relationship(back_populates="organization")  # noqa: F821
