"""Pydantic schemas for EmailDraft CRUD."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EmailGoal
from app.schemas.person import PersonResponse


class EmailDraftCreate(BaseModel):
    """Payload for creating an outreach draft."""

    person_id: UUID
    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)
    goal: EmailGoal | None = EmailGoal.INTRO
    generation_context: dict | None = None
    is_sent: bool = False


class EmailDraftUpdate(BaseModel):
    """Partial update — only provided fields are applied."""

    person_id: UUID | None = None
    subject: str | None = Field(default=None, min_length=1, max_length=500)
    body: str | None = Field(default=None, min_length=1)
    goal: EmailGoal | None = None
    generation_context: dict | None = None
    is_sent: bool | None = None
    sent_at: datetime | None = None


class EmailDraftResponse(BaseModel):
    """Draft as returned by list endpoints (no nested person)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    person_id: UUID
    subject: str
    body: str
    goal: EmailGoal
    generation_context: dict | None
    is_sent: bool
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EmailDraftWithPersonResponse(EmailDraftResponse):
    """Draft detail with eagerly loaded person."""

    person: PersonResponse


class EmailDraftListResponse(BaseModel):
    """Paginated draft list."""

    items: list[EmailDraftResponse]
    total: int
    limit: int
    offset: int
