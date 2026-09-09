"""Pydantic schemas for Person CRUD."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import EmailStatus
from app.schemas.company import CompanyResponse

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_LINKEDIN_PREFIXES = (
    "https://linkedin.com/in/",
    "http://linkedin.com/in/",
    "https://www.linkedin.com/in/",
    "http://www.linkedin.com/in/",
)


def normalize_linkedin_url(value: str) -> str:
    """Require a LinkedIn /in/ profile URL. `www.` is accepted (real LinkedIn URLs)."""
    url = value.strip()
    lowered = url.lower()
    if not lowered.startswith(_LINKEDIN_PREFIXES):
        raise ValueError(
            "linkedin_url must start with https://linkedin.com/in/ or https://www.linkedin.com/in/"
        )
    return url.rstrip("/")


def normalize_email(value: str) -> str:
    """Lowercase and reject obviously malformed emails."""
    email = value.strip().lower()
    if not _EMAIL_RE.fullmatch(email):
        raise ValueError("Invalid email format")
    return email


class PersonCreate(BaseModel):
    """Payload for creating a person."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    linkedin_url: str | None = Field(default=None, max_length=500)
    email: str | None = Field(default=None, max_length=255)
    email_status: EmailStatus | None = EmailStatus.UNKNOWN
    title: str | None = Field(default=None, max_length=255)
    company_id: UUID | None = None
    raw_linkedin_data: dict | None = None

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, value: str | None) -> str | None:
        """Reject non-LinkedIn profile URLs when the field is set."""
        if value is None:
            return None
        return normalize_linkedin_url(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        """Normalize email when present."""
        if value is None:
            return None
        return normalize_email(value)


class PersonUpdate(BaseModel):
    """Partial update — only provided fields are applied."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    linkedin_url: str | None = Field(default=None, max_length=500)
    email: str | None = Field(default=None, max_length=255)
    email_status: EmailStatus | None = None
    title: str | None = Field(default=None, max_length=255)
    company_id: UUID | None = None
    raw_linkedin_data: dict | None = None

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, value: str | None) -> str | None:
        """Normalize LinkedIn URL when present."""
        if value is None:
            return None
        return normalize_linkedin_url(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        """Normalize email when present."""
        if value is None:
            return None
        return normalize_email(value)


class PersonCompanyAssign(BaseModel):
    """Bind a person to an existing company."""

    company_id: UUID


class PersonResponse(BaseModel):
    """Person as returned by list endpoints (no nested company)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    linkedin_url: str | None
    email: str | None
    email_status: EmailStatus
    title: str | None
    company_id: UUID | None
    raw_linkedin_data: dict | None
    created_at: datetime
    updated_at: datetime


class PersonWithCompanyResponse(PersonResponse):
    """Person detail with eagerly loaded company."""

    company: CompanyResponse | None = None


class PersonListResponse(BaseModel):
    """Paginated person list."""

    items: list[PersonResponse]
    total: int
    limit: int
    offset: int
