"""Pydantic schemas for email finder."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.email_candidate import EmailCandidateSource, EmailCandidateStatus


class EmailCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    person_id: UUID
    email: str
    source: EmailCandidateSource
    status: EmailCandidateStatus
    confidence: float
    pattern_used: str | None = None
    is_primary: bool
    verified_at: datetime | None = None
    verification_details: dict | None = None
    created_at: datetime


class EmailFindRequest(BaseModel):
    person_id: UUID
    domain: str | None = Field(default=None, description="Defaults to the person's company domain")
    prefer_source: EmailCandidateSource | None = None
    use_hunter: bool = True
    use_apollo: bool = True
    use_smtp: bool = False


class EmailFindResponse(BaseModel):
    person_id: UUID
    candidates: list[EmailCandidateResponse]
    primary_email: str | None = None
    best_confidence: float = 0.0
    sources_used: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
