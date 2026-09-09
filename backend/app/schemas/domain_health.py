"""Pydantic schemas for DomainHealth CRUD."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.company import normalize_domain


class DomainHealthCreate(BaseModel):
    """Payload for creating or upserting a domain health snapshot."""

    domain: str = Field(..., min_length=3, max_length=255, examples=["gmail.com"])
    spf_record: str | None = None
    spf_valid: bool = False
    dkim_record: str | None = None
    dkim_valid: bool = False
    dmarc_record: str | None = None
    dmarc_policy: str | None = Field(default=None, max_length=50)
    mx_records: list[str] | None = None
    checked_at: datetime | None = None

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        """Reuse company domain normalization (scheme/www/path stripped)."""
        return normalize_domain(value)


class DomainHealthUpdate(BaseModel):
    """Partial update — only provided fields are applied."""

    domain: str | None = Field(default=None, min_length=3, max_length=255)
    spf_record: str | None = None
    spf_valid: bool | None = None
    dkim_record: str | None = None
    dkim_valid: bool | None = None
    dmarc_record: str | None = None
    dmarc_policy: str | None = Field(default=None, max_length=50)
    mx_records: list[str] | None = None
    checked_at: datetime | None = None

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str | None) -> str | None:
        """Normalize domain when present."""
        if value is None:
            return None
        return normalize_domain(value)


class DomainHealthResponse(BaseModel):
    """Domain health snapshot as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    domain: str
    spf_record: str | None
    spf_valid: bool
    dkim_record: str | None
    dkim_valid: bool
    dmarc_record: str | None
    dmarc_policy: str | None
    mx_records: list[str] | None
    checked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DomainHealthListResponse(BaseModel):
    """Paginated domain health list."""

    items: list[DomainHealthResponse]
    total: int
    limit: int
    offset: int
