"""Pydantic schemas for Instantly-shaped sequences (no send)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.outreach_sequence import EnrollmentStatus, SequenceStatus


class SequenceStep(BaseModel):
    delay_days: int = Field(default=0, ge=0, le=90)
    goal: str = "meeting"
    template_hint: str = ""


class SequenceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    mailbox_id: UUID | None = None
    status: SequenceStatus = SequenceStatus.DRAFT
    steps: list[SequenceStep] = Field(default_factory=list)


class SequenceEnrollRequest(BaseModel):
    person_id: UUID


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sequence_id: UUID
    person_id: UUID
    current_step: int
    status: EnrollmentStatus
    created_at: datetime


class SequenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    mailbox_id: UUID | None
    status: SequenceStatus
    steps: list
    created_at: datetime


class SequenceTickResponse(BaseModel):
    sequence_id: UUID
    advanced: int
    completed: int
    emails_sent: int = 0
