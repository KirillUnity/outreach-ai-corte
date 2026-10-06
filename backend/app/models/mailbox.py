"""Mailbox used as a sending identity for warmup simulation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.warmup_event import WarmupEvent


class MailboxStatus(str, Enum):
    NEW = "new"
    WARMING = "warming"
    WARMED = "warmed"
    PAUSED = "paused"
    BANNED = "banned"


class Mailbox(UUIDMixin, TimestampMixin, Base):
    """Sending mailbox whose reputation is simulated over warmup days 1–30."""

    __tablename__ = "mailboxes"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[MailboxStatus] = mapped_column(
        SAEnum(MailboxStatus, name="mailbox_status", native_enum=False, length=32),
        default=MailboxStatus.NEW,
        server_default=MailboxStatus.NEW.value,
        nullable=False,
    )
    warmup_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    warmup_day: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    daily_limit: Mapped[int] = mapped_column(Integer, default=5, server_default="5", nullable=False)
    emails_sent_today: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    total_sent: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    total_opened: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    total_replied: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    total_bounced: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    total_spam_reports: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    reputation_score: Mapped[float] = mapped_column(
        Float,
        default=50.0,
        server_default="50.0",
        nullable=False,
    )

    last_warmup_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    warmup_events: Mapped[list[WarmupEvent]] = relationship(
        back_populates="mailbox",
        cascade="all, delete-orphan",
    )
