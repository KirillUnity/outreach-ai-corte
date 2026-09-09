"""Domain health (DNS / email authentication) ORM model."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class DomainHealth(UUIDMixin, TimestampMixin, Base):
    """SPF / DKIM / DMARC / MX snapshot for a sending or target domain."""

    __tablename__ = "domain_health"

    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    spf_record: Mapped[str | None] = mapped_column(Text, nullable=True)
    spf_valid: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    dkim_record: Mapped[str | None] = mapped_column(Text, nullable=True)
    dkim_valid: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    dmarc_record: Mapped[str | None] = mapped_column(Text, nullable=True)
    dmarc_policy: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mx_records: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
