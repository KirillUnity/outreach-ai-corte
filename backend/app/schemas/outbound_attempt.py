"""Read model for one saved outbound vendor call."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OutboundAttemptResponse(BaseModel):
    """Fields a caller can open in the attempt list. There is no send action."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target: str
    attempt_count: int
    last_error: str | None
    next_attempt_at: datetime | None
    status: str
