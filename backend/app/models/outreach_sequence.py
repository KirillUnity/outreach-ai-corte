"""Instantly-shaped outreach sequences. No SMTP — steps only move in Postgres."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.mailbox import Mailbox
    from app.models.person import Person


class SequenceStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"


class EnrollmentStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    STOPPED = "stopped"


class OutreachSequence(UUIDMixin, TimestampMixin, Base):
    """Ordered follow-up steps. Sending is a later product; this table is the campaign shape."""

    __tablename__ = "outreach_sequences"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    mailbox_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("mailboxes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[SequenceStatus] = mapped_column(
        SAEnum(SequenceStatus, name="outreach_sequence_status", native_enum=False, length=32),
        default=SequenceStatus.DRAFT,
        server_default=SequenceStatus.DRAFT.value,
        nullable=False,
    )
    steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    mailbox: Mapped["Mailbox | None"] = relationship()
    enrollments: Mapped[list["OutreachSequenceEnrollment"]] = relationship(
        back_populates="sequence",
        cascade="all, delete-orphan",
    )


class OutreachSequenceEnrollment(UUIDMixin, TimestampMixin, Base):
    """A person walking through a sequence. tick() only increments current_step."""

    __tablename__ = "outreach_sequence_enrollments"
    __table_args__ = (
        UniqueConstraint("sequence_id", "person_id", name="uq_sequence_enrollment_person"),
    )

    sequence_id: Mapped[UUID] = mapped_column(
        ForeignKey("outreach_sequences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    current_step: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    status: Mapped[EnrollmentStatus] = mapped_column(
        SAEnum(EnrollmentStatus, name="outreach_enrollment_status", native_enum=False, length=32),
        default=EnrollmentStatus.PENDING,
        server_default=EnrollmentStatus.PENDING.value,
        nullable=False,
    )

    sequence: Mapped[OutreachSequence] = relationship(back_populates="enrollments")
    person: Mapped["Person"] = relationship()
