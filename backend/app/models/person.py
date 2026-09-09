"""Person ORM model."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import EmailStatus

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.email_draft import EmailDraft


class Person(UUIDMixin, TimestampMixin, Base):
    """A contact at a company (or unaffiliated if company was deleted)."""

    __tablename__ = "persons"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    linkedin_url: Mapped[str | None] = mapped_column(
        String(500),
        unique=True,
        nullable=True,
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_status: Mapped[EmailStatus] = mapped_column(
        Enum(EmailStatus, name="email_status", native_enum=False, length=32),
        default=EmailStatus.UNKNOWN,
        server_default=EmailStatus.UNKNOWN.value,
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_linkedin_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    company: Mapped["Company | None"] = relationship(back_populates="persons")
    email_drafts: Mapped[list["EmailDraft"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )
