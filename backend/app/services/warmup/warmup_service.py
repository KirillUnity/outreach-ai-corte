"""CRUD + tick helpers for warmup mailboxes."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.mailbox import Mailbox, MailboxStatus
from app.models.warmup_event import WarmupEvent, WarmupEventType
from app.schemas.mailbox import MailboxCreate, MailboxStatsResponse, WarmupTimelinePoint
from app.services.exceptions import DuplicateError, NotFoundError
from app.services.warmup.warmup_emulator import WarmupEmulator


def mailbox_rates(row: Mailbox) -> tuple[float, float, float]:
    sent = row.total_sent or 0
    if sent <= 0:
        return 0.0, 0.0, 0.0
    return row.total_opened / sent, row.total_replied / sent, row.total_bounced / sent


class WarmupService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.emulator = WarmupEmulator(db, settings)

    async def create_mailbox(self, data: MailboxCreate) -> Mailbox:
        email = str(data.email).strip().lower()
        domain = email.split("@", 1)[1] if "@" in email else ""
        existing = await self.get_by_email(email)
        if existing is not None:
            raise DuplicateError(f"Mailbox '{email}' already exists")
        row = Mailbox(
            email=email,
            domain=domain,
            display_name=data.display_name,
            status=MailboxStatus.NEW,
            reputation_score=50.0,
        )
        self.db.add(row)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise DuplicateError(f"Mailbox '{email}' already exists") from None
        await self.db.refresh(row)
        return row

    async def get_mailbox(self, mailbox_id: UUID) -> Mailbox | None:
        return await self.db.get(Mailbox, mailbox_id)

    async def get_by_email(self, email: str) -> Mailbox | None:
        result = await self.db.execute(select(Mailbox).where(Mailbox.email == email.strip().lower()))
        return result.scalar_one_or_none()

    async def list_mailboxes(
        self,
        status: MailboxStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Mailbox], int]:
        filters = []
        if status is not None:
            filters.append(Mailbox.status == status)
        count_stmt = select(func.count()).select_from(Mailbox)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = (await self.db.execute(count_stmt)).scalar_one()
        stmt = select(Mailbox).order_by(Mailbox.created_at.desc()).limit(limit).offset(offset)
        if filters:
            stmt = stmt.where(*filters)
        rows = list((await self.db.execute(stmt)).scalars().all())
        return rows, total

    async def start_warmup(self, mailbox_id: UUID, reset: bool = False) -> Mailbox:
        return await self.emulator.start_warmup(mailbox_id, reset=reset)

    async def run_tick(self, mailbox_id: UUID) -> dict:
        events_created = await self.emulator.tick(mailbox_id)
        mailbox = await self._require(mailbox_id)
        return {
            "events_created": events_created,
            "new_reputation": mailbox.reputation_score,
            "new_day": mailbox.warmup_day,
            "status": mailbox.status,
        }

    async def pause_mailbox(self, mailbox_id: UUID) -> Mailbox:
        mailbox = await self._require(mailbox_id)
        mailbox.status = MailboxStatus.PAUSED
        await self.db.commit()
        await self.db.refresh(mailbox)
        return mailbox

    async def resume_mailbox(self, mailbox_id: UUID) -> Mailbox:
        mailbox = await self._require(mailbox_id)
        mailbox.status = MailboxStatus.WARMING
        if mailbox.warmup_day < 1:
            mailbox.warmup_day = 1
        await self.db.commit()
        await self.db.refresh(mailbox)
        return mailbox

    async def delete_mailbox(self, mailbox_id: UUID) -> bool:
        mailbox = await self.get_mailbox(mailbox_id)
        if mailbox is None:
            return False
        await self.db.delete(mailbox)
        await self.db.commit()
        return True

    async def get_stats(self, mailbox_id: UUID) -> MailboxStatsResponse:
        mailbox = await self._require(mailbox_id)
        open_rate, reply_rate, bounce_rate = mailbox_rates(mailbox)
        return MailboxStatsResponse(
            mailbox_id=mailbox.id,
            email=mailbox.email,
            warmup_day=mailbox.warmup_day,
            reputation_score=mailbox.reputation_score,
            open_rate=open_rate,
            reply_rate=reply_rate,
            bounce_rate=bounce_rate,
            daily_limit=mailbox.daily_limit,
            emails_sent_today=mailbox.emails_sent_today,
            status=mailbox.status,
        )

    async def get_events(self, mailbox_id: UUID, limit: int = 50) -> list[WarmupEvent]:
        await self._require(mailbox_id)
        stmt = (
            select(WarmupEvent)
            .where(WarmupEvent.mailbox_id == mailbox_id)
            .order_by(WarmupEvent.created_at.desc())
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_timeline(self, mailbox_id: UUID) -> list[WarmupTimelinePoint]:
        await self._require(mailbox_id)
        sent = func.coalesce(
            func.sum(case((WarmupEvent.event_type == WarmupEventType.SENT, 1), else_=0)),
            0,
        )
        opened = func.coalesce(
            func.sum(case((WarmupEvent.event_type == WarmupEventType.OPENED, 1), else_=0)),
            0,
        )
        replied = func.coalesce(
            func.sum(case((WarmupEvent.event_type == WarmupEventType.REPLIED, 1), else_=0)),
            0,
        )
        stmt = (
            select(WarmupEvent.warmup_day, sent, opened, replied)
            .where(WarmupEvent.mailbox_id == mailbox_id)
            .group_by(WarmupEvent.warmup_day)
            .order_by(WarmupEvent.warmup_day)
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            WarmupTimelinePoint(day=int(day), sent=int(s), opened=int(o), replied=int(r))
            for day, s, o, r in rows
        ]

    async def _require(self, mailbox_id: UUID) -> Mailbox:
        mailbox = await self.get_mailbox(mailbox_id)
        if mailbox is None:
            raise NotFoundError(f"Mailbox '{mailbox_id}' not found")
        return mailbox
