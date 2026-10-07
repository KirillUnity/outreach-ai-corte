"""Log of one CRM upsert attempt."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.person import Person


class CrmSyncEvent(UUIDMixin, TimestampMixin, Base):
    """Outbound lead upsert. status is ok | error. Never stores vendor passwords."""

    __tablename__ = "crm_sync_events"

    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    remote_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    person: Mapped["Person"] = relationship()
