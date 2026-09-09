"""Email draft ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import EmailGoal

if TYPE_CHECKING:
    from app.models.person import Person


class EmailDraft(UUIDMixin, TimestampMixin, Base):
    """AI-generated outreach email tied to a person."""

    __tablename__ = "email_drafts"

    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    goal: Mapped[EmailGoal] = mapped_column(
        Enum(EmailGoal, name="email_goal", native_enum=False, length=32),
        default=EmailGoal.INTRO,
        server_default=EmailGoal.INTRO.value,
        nullable=False,
    )
    generation_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    person: Mapped["Person"] = relationship(back_populates="email_drafts")
