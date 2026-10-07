"""CRM sync HTTP schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CrmSyncResponse(BaseModel):
    event_id: UUID
    provider: str
    status: str
    remote_id: str | None = None


class CrmSyncEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    person_id: UUID
    provider: str
    status: str
    remote_id: str | None = None
    request_payload: dict | None = None
    response_payload: dict | None = None
    created_at: datetime


class CrmEventListResponse(BaseModel):
    items: list[CrmSyncEventResponse]
    total: int = 0
