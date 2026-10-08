"""Pydantic schemas for mailbox warmup."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.mailbox import Mailbox, MailboxStatus
from app.models.warmup_event import WarmupEventType


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


class MailboxCreate(BaseModel):
    email: EmailStr
    display_name: str | None = None


class MailboxResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    domain: str
    display_name: str | None
    status: MailboxStatus
    warmup_day: int
    daily_limit: int
    emails_sent_today: int
    total_sent: int
    total_opened: int
    total_replied: int
    total_bounced: int
    total_spam_reports: int
    reputation_score: float
    open_rate: float
    reply_rate: float
    bounce_rate: float
    warmup_started_at: datetime | None
    last_warmup_event_at: datetime | None
    created_at: datetime

    @classmethod
    def from_mailbox(cls, row: Mailbox) -> MailboxResponse:
        sent = row.total_sent or 0
        return cls(
            id=row.id,
            email=row.email,
            domain=row.domain,
            display_name=row.display_name,
            status=row.status,
            warmup_day=row.warmup_day,
            daily_limit=row.daily_limit,
            emails_sent_today=row.emails_sent_today,
            total_sent=row.total_sent,
            total_opened=row.total_opened,
            total_replied=row.total_replied,
            total_bounced=row.total_bounced,
            total_spam_reports=row.total_spam_reports,
            reputation_score=row.reputation_score,
            open_rate=_ratio(row.total_opened, sent),
            reply_rate=_ratio(row.total_replied, sent),
            bounce_rate=_ratio(row.total_bounced, sent),
            warmup_started_at=row.warmup_started_at,
            last_warmup_event_at=row.last_warmup_event_at,
            created_at=row.created_at,
        )


class MailboxListResponse(BaseModel):
    items: list[MailboxResponse]
    total: int
    limit: int
    offset: int


class MailboxStatsResponse(BaseModel):
    mailbox_id: UUID
    email: str
    warmup_day: int
    reputation_score: float
    open_rate: float
    reply_rate: float
    bounce_rate: float
    daily_limit: int
    emails_sent_today: int
    status: MailboxStatus


class WarmupEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    mailbox_id: UUID
    peer_email: str
    event_type: WarmupEventType
    warmup_day: int
    created_at: datetime


class WarmupStartRequest(BaseModel):
    mailbox_ids: list[UUID] | None = None
    reset_progress: bool = False


class WarmupTickResponse(BaseModel):
    mailboxes_processed: int
    events_created: int
    mailboxes_banned: int
    mailboxes_warmed: int
    duration_seconds: float = 0.0


class WarmupMailboxTickResponse(BaseModel):
    events_created: int
    new_reputation: float
    new_day: int
    status: MailboxStatus


class WarmupTimelinePoint(BaseModel):
    day: int
    sent: int
    opened: int
    replied: int
