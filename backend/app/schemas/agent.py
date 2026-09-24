"""Request/response schemas for the outreach agent."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import EmailGoal


class AgentRunRequest(BaseModel):
    """Start one autonomous outreach graph run."""

    person_id: UUID
    goal: EmailGoal = EmailGoal.MEETING
    sender_name: str = Field(..., min_length=1)
    sender_title: str = Field(..., min_length=1)
    sender_company: str = Field(..., min_length=1)
    language: str = "en"
    max_words: int = Field(default=120, ge=50, le=300)


class AgentRunResponse(BaseModel):
    """Decision plus the draft the graph produced (or held/rejected)."""

    draft_id: UUID | None = None
    decision: str
    decision_reason: str | None = None
    email_subject: str | None = None
    email_body: str | None = None
    validation_errors: list[str] = []
    deliverability_ok: bool | None = None
    tokens_input: int = 0
    tokens_output: int = 0
    estimated_cost_usd: float = 0.0
    iterations: int = 0
    errors: list[str] = []
    created_at: datetime | None = None


class AgentRunListResponse(BaseModel):
    """Paginated history of graph runs."""

    items: list[AgentRunResponse]
    total: int
    limit: int
    offset: int
