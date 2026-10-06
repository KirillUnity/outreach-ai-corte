"""Email guesses and provider hits attached to a person."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.person import Person


class EmailCandidateSource(str, Enum):
    PATTERN = "pattern"
    HUNTER = "hunter"
    APOLLO = "apollo"
    MANUAL = "manual"
    LINKEDIN = "linkedin"
    GUESS = "guess"


class EmailCandidateStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    INVALID = "invalid"
    CATCHALL = "catchall"
    UNKNOWN = "unknown"


class EmailCandidate(UUIDMixin, TimestampMixin, Base):
    """One possible address for a person; several sources can coexist."""

    __tablename__ = "email_candidates"
    __table_args__ = (UniqueConstraint("person_id", "email", name="uq_email_candidates_person_email"),)

    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[EmailCandidateSource] = mapped_column(
        SAEnum(EmailCandidateSource, name="email_candidate_source", native_enum=False, length=32),
        nullable=False,
    )
    status: Mapped[EmailCandidateStatus] = mapped_column(
        SAEnum(EmailCandidateStatus, name="email_candidate_status", native_enum=False, length=32),
        default=EmailCandidateStatus.PENDING,
        server_default=EmailCandidateStatus.PENDING.value,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0", nullable=False)
    pattern_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_provider_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    person: Mapped[Person] = relationship(back_populates="email_candidates")

    def __repr__(self) -> str:
        return f"<EmailCandidate {self.email} ({self.source.value}, {self.status.value})>"
