"""One row per external call target. Retries update this row."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

STATUS_FAILED = "failed"
STATUS_SUCCEEDED = "succeeded"


class OutboundAttemptStatus(str, Enum):
    """Vendor call outcome stored on `outbound_attempts.status`."""

    FAILED = STATUS_FAILED
    SUCCEEDED = STATUS_SUCCEEDED


class AwareDateTime(TypeDecorator[datetime]):
    """Timezone-aware UTC datetimes, including values read back from SQLite."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class OutboundAttempt(UUIDMixin, TimestampMixin, Base):
    """Rate-limit and success history for a single outbound target."""

    __tablename__ = "outbound_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('failed', 'succeeded')",
            name="ck_outbound_attempts_status",
        ),
    )

    target: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(AwareDateTime(), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
