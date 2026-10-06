"""Single interaction in the warmup peer network."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.mailbox import Mailbox


class WarmupEventType(str, Enum):
    SENT = "sent"
    OPENED = "opened"
    REPLIED = "replied"
    BOUNCED = "bounced"
    SPAM_REPORT = "spam_report"
    MARKED_IMPORTANT = "marked_important"


class WarmupEvent(UUIDMixin, TimestampMixin, Base):
    """One simulated send or engagement against a peer mailbox."""

    __tablename__ = "warmup_events"

    mailbox_id: Mapped[UUID] = mapped_column(
        ForeignKey("mailboxes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    peer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[WarmupEventType] = mapped_column(
        SAEnum(WarmupEventType, name="warmup_event_type", native_enum=False, length=32),
        nullable=False,
    )
    warmup_day: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    mailbox: Mapped[Mailbox] = relationship(back_populates="warmup_events")
