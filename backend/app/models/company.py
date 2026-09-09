"""Company ORM model."""

from typing import TYPE_CHECKING

from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import CompanySize

if TYPE_CHECKING:
    from app.models.person import Person


class Company(UUIDMixin, TimestampMixin, Base):
    """A target company for outreach, keyed by unique domain."""

    __tablename__ = "companies"

    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size: Mapped[CompanySize | None] = mapped_column(
        Enum(CompanySize, name="company_size", native_enum=False, length=32),
        nullable=True,
    )
    raw_site_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    persons: Mapped[list["Person"]] = relationship(
        back_populates="company",
        cascade="save-update, merge",
    )
