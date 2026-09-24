"""Pydantic schemas for Company CRUD."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import CompanySize

_SCHEME_RE = re.compile(r"^https?://", re.IGNORECASE)
_WWW_RE = re.compile(r"^www\.", re.IGNORECASE)
_DOMAIN_RE = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$",
)


def normalize_domain(value: str) -> str:
    """Strip scheme, www, path and validate a hostname-like domain."""
    domain = value.strip().lower()
    domain = _SCHEME_RE.sub("", domain)
    domain = _WWW_RE.sub("", domain)
    domain = domain.split("/", maxsplit=1)[0]
    domain = domain.split("?", maxsplit=1)[0]
    domain = domain.split(":", maxsplit=1)[0]
    domain = domain.rstrip(".")
    if not domain or not _DOMAIN_RE.fullmatch(domain):
        raise ValueError("Invalid domain format. Expected a hostname like example.com")
    return domain


class CompanyCreate(BaseModel):
    """Payload for creating a company."""

    domain: str = Field(..., min_length=3, max_length=255, examples=["acme.com"])
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    industry: str | None = Field(default=None, max_length=255)
    size: CompanySize | None = None

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        """Normalize and reject URLs / malformed hostnames."""
        return normalize_domain(value)


class CompanyUpdate(BaseModel):
    """Partial update — only provided fields are applied."""

    domain: str | None = Field(default=None, min_length=3, max_length=255)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    industry: str | None = Field(default=None, max_length=255)
    size: CompanySize | None = None
    raw_site_text: str | None = None

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str | None) -> str | None:
        """Normalize domain when present."""
        if value is None:
            return None
        return normalize_domain(value)


class CompanyResponse(BaseModel):
    """Company as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    domain: str
    name: str
    description: str | None
    industry: str | None
    size: CompanySize | None
    raw_site_text: str | None
    created_at: datetime
    updated_at: datetime


class CompanyListResponse(BaseModel):
    """Paginated company list."""

    items: list[CompanyResponse]
    total: int
    limit: int
    offset: int


class CompanyResearchResponse(BaseModel):
    """Result of POST /companies/{domain}/research."""

    company: CompanyResponse
    pages_parsed: int
    chunks_indexed: int = 0
    errors: list[str] = []
    research_duration_seconds: float


class RAGChunk(BaseModel):
    """One retrieved chunk from Chroma."""

    text: str
    score: float | None = None
    chunk_index: int | None = None
    metadata: dict = Field(default_factory=dict)


class CompanyContextResponse(BaseModel):
    """Semantic search over a company's indexed site text."""

    domain: str
    query: str
    chunks: list[RAGChunk]
