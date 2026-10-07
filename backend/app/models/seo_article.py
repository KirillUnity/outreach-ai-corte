"""SEO article persistence model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.company import Company


class SEOArticle(UUIDMixin, TimestampMixin, Base):
    """A generated long-form article awaiting explicit publication."""

    __tablename__ = "seo_articles"

    company_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), unique=True, index=True, nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="ru", server_default="ru")
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    keywords: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    meta_title: Mapped[str | None] = mapped_column(String(60), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(160), nullable=True)
    rag_context_used: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    tokens_input: Mapped[int] = mapped_column(default=0, server_default="0")
    tokens_output: Mapped[int] = mapped_column(default=0, server_default="0")
    estimated_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 8), default=0, server_default="0"
    )
    generation_prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    publish_channel: Mapped[str] = mapped_column(
        String(20), default="mock", server_default="mock"
    )
    publish_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    internal_links: Mapped[list[dict[str, str]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    keyword_primary: Mapped[str | None] = mapped_column(String(255), nullable=True)

    company: Mapped["Company | None"] = relationship()
