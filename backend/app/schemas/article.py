"""Pydantic schemas for SEO article generation and publishing."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ArticleCreate(BaseModel):
    """Create an article manually."""

    company_id: UUID | None = None
    title: str = Field(min_length=1, max_length=300)
    slug: str = Field(min_length=1, max_length=300, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    body_markdown: str = Field(min_length=1)
    language: str = Field(default="ru", min_length=2, max_length=10)


class ArticleGenerateRequest(BaseModel):
    """Parameters for RAG-backed article generation."""

    company_domain: str = Field(min_length=3, max_length=255)
    keyword: str = Field(min_length=2, max_length=255)
    language: str = Field(default="ru", min_length=2, max_length=10)
    max_words: int = Field(default=800, ge=100, le=2000)


class ArticleUpdate(BaseModel):
    """Fields editable by an operator before publication."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    body_markdown: str | None = Field(default=None, min_length=1)
    meta_title: str | None = Field(default=None, max_length=60)
    meta_description: str | None = Field(default=None, max_length=160)
    keyword_primary: str | None = Field(default=None, max_length=255)
    keywords: list[str] | None = None
    internal_links: list[dict[str, str]] | None = None
    publish_channel: Literal["mock", "webhook"] | None = None


class ArticleScheduleRequest(BaseModel):
    """Schedule an article for a future tick."""

    scheduled_at: datetime


class InternalLink(BaseModel):
    """Validated internal link shown with an article."""

    anchor: str
    url: str


class ArticleResponse(BaseModel):
    """Serialized SEO article."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID | None
    title: str
    slug: str
    body_markdown: str
    language: str
    status: str
    keywords: list[str]
    meta_title: str | None
    meta_description: str | None
    rag_context_used: list[dict[str, object]]
    tokens_input: int
    tokens_output: int
    estimated_cost_usd: Decimal
    generation_prompt_version: str
    scheduled_at: datetime | None
    published_at: datetime | None
    publish_channel: str
    publish_url: str | None
    internal_links: list[dict[str, str]]
    keyword_primary: str | None
    created_at: datetime
    updated_at: datetime


class ArticleListResponse(BaseModel):
    """Paginated articles."""

    items: list[ArticleResponse]
    total: int
    limit: int
    offset: int


class TickDueResponse(BaseModel):
    """Result of processing scheduled articles."""

    processed: int
    published: int
    failed: int
