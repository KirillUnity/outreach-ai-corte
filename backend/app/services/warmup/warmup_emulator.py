"""Simulate daily warmup sends against a peer network."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.mailbox import Mailbox, MailboxStatus
from app.models.warmup_event import WarmupEvent, WarmupEventType
from app.services.exceptions import NotFoundError
from app.services.warmup.peer_network import PeerNetwork

logger = logging.getLogger(__name__)


class WarmupEmulator:
    """One tick = one simulated warmup day for a mailbox."""

    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        *,
        peers: PeerNetwork | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        cfg = settings.warmup
        self.peers = peers or PeerNetwork(size=cfg.peer_network_size, seed=42)
        if rng is not None:
            self.rng = rng
        elif cfg.rng_seed is not None:
            self.rng = random.Random(cfg.rng_seed)
        else:
            self.rng = random.Random()

    async def start_warmup(self, mailbox_id: UUID, reset: bool = False) -> Mailbox:
        mailbox = await self._get_mailbox(mailbox_id)
        if reset:
            mailbox.warmup_day = 0
            mailbox.emails_sent_today = 0
            mailbox.total_sent = 0
            mailbox.total_opened = 0
            mailbox.total_replied = 0
            mailbox.total_bounced = 0
            mailbox.total_spam_reports = 0
            mailbox.reputation_score = 50.0
            mailbox.notes = None
        mailbox.status = MailboxStatus.WARMING
        mailbox.warmup_started_at = datetime.now(timezone.utc)
        mailbox.warmup_day = 1
        mailbox.daily_limit = self._limit_for_day(1)
        mailbox.emails_sent_today = 0
        await self.db.commit()
        await self.db.refresh(mailbox)
        logger.info("warmup started mailbox=%s day=1 limit=%s", mailbox.email, mailbox.daily_limit)
        return mailbox

    async def tick(self, mailbox_id: UUID) -> int:
        mailbox = await self._get_mailbox(mailbox_id)
        if mailbox.status in {MailboxStatus.PAUSED, MailboxStatus.BANNED}:
            return 0
        if mailbox.status == MailboxStatus.NEW:
            mailbox.status = MailboxStatus.WARMING
            mailbox.warmup_started_at = mailbox.warmup_started_at or datetime.now(timezone.utc)
            if mailbox.warmup_day < 1:
                mailbox.warmup_day = 1
        day = mailbox.warmup_day if mailbox.warmup_day >= 1 else 1
        mailbox.warmup_day = day
        limit = self._limit_for_day(day)
        mailbox.daily_limit = limit
        send_count = min(limit, self.settings.warmup.max_emails_per_tick)

        cfg = self.settings.warmup
        opened = replied = bounced = spam = 0
        events_created = 0
        now = datetime.now(timezone.utc)

        for _ in range(send_count):
            peers = self.peers.get_random_peers(1, exclude_domain=mailbox.domain)
            peer = peers[0] if peers else "peer1@warmup-network.local"
            self.db.add(
                WarmupEvent(
                    mailbox_id=mailbox.id,
                    peer_email=peer,
                    event_type=WarmupEventType.SENT,
                    warmup_day=day,
                )
            )
            events_created += 1
            if self.rng.random() < cfg.peer_bounce_rate:
                self.db.add(
                    WarmupEvent(
                        mailbox_id=mailbox.id,
                        peer_email=peer,
                        event_type=WarmupEventType.BOUNCED,
                        warmup_day=day,
                    )
                )
                events_created += 1
                bounced += 1
                continue
            reputation = mailbox.reputation_score if mailbox.reputation_score is not None else 0.0
            open_p = min(1.0, cfg.peer_open_rate * (reputation / 50.0))
            if self.rng.random() < open_p:
                self.db.add(
                    WarmupEvent(
                        mailbox_id=mailbox.id,
                        peer_email=peer,
                        event_type=WarmupEventType.OPENED,
                        warmup_day=day,
                    )
                )
                events_created += 1
                opened += 1
            if self.rng.random() < cfg.peer_reply_rate:
                self.db.add(
                    WarmupEvent(
                        mailbox_id=mailbox.id,
                        peer_email=peer,
                        event_type=WarmupEventType.REPLIED,
                        warmup_day=day,
                    )
                )
                events_created += 1
                replied += 1
            if self.rng.random() < cfg.peer_spam_rate:
                self.db.add(
                    WarmupEvent(
                        mailbox_id=mailbox.id,
                        peer_email=peer,
                        event_type=WarmupEventType.SPAM_REPORT,
                        warmup_day=day,
                    )
                )
                events_created += 1
                spam += 1
            if self.rng.random() < cfg.peer_important_rate:
                self.db.add(
                    WarmupEvent(
                        mailbox_id=mailbox.id,
                        peer_email=peer,
                        event_type=WarmupEventType.MARKED_IMPORTANT,
                        warmup_day=day,
                    )
                )
                events_created += 1

        mailbox.total_sent = (mailbox.total_sent or 0) + send_count
        mailbox.total_opened = (mailbox.total_opened or 0) + opened
        mailbox.total_replied = (mailbox.total_replied or 0) + replied
        mailbox.total_bounced = (mailbox.total_bounced or 0) + bounced
        mailbox.total_spam_reports = (mailbox.total_spam_reports or 0) + spam
        mailbox.emails_sent_today = send_count
        mailbox.last_warmup_event_at = now
        mailbox.reputation_score = self._compute_reputation(mailbox)

        mailbox.warmup_day = day + 1
        mailbox.daily_limit = self._limit_for_day(mailbox.warmup_day)

        if mailbox.reputation_score < cfg.reputation_ban_threshold:
            mailbox.status = MailboxStatus.BANNED
            logger.warning("mailbox banned email=%s score=%s", mailbox.email, mailbox.reputation_score)
        elif (
            mailbox.reputation_score >= cfg.reputation_warmed_threshold
            and mailbox.warmup_day >= 30
        ):
            mailbox.status = MailboxStatus.WARMED
            logger.info("mailbox warmed email=%s score=%s", mailbox.email, mailbox.reputation_score)

        await self.db.commit()
        await self.db.refresh(mailbox)
        return events_created

    def _compute_reputation(self, mailbox: Mailbox) -> float:
        sent = mailbox.total_sent or 0
        if sent <= 0:
            return float(mailbox.reputation_score or 50.0)
        open_rate = mailbox.total_opened / sent
        reply_rate = mailbox.total_replied / sent
        bounce_rate = mailbox.total_bounced / sent
        spam_rate = mailbox.total_spam_reports / sent
        score = (
            50.0
            + (open_rate - 0.5) * 40
            + reply_rate * 100
            - bounce_rate * 500
            - spam_rate * 5000
        )
        cfg = self.settings.warmup
        return max(cfg.reputation_min, min(cfg.reputation_max, score))

    async def tick_all(self) -> dict[str, int]:
        result = await self.db.execute(
            select(Mailbox).where(Mailbox.status == MailboxStatus.WARMING)
        )
        rows = list(result.scalars().all())
        events_created = 0
        banned = 0
        warmed = 0
        for mailbox in rows:
            before = mailbox.status
            events_created += await self.tick(mailbox.id)
            await self.db.refresh(mailbox)
            if before != MailboxStatus.BANNED and mailbox.status == MailboxStatus.BANNED:
                banned += 1
            if before != MailboxStatus.WARMED and mailbox.status == MailboxStatus.WARMED:
                warmed += 1
        return {
            "mailboxes_processed": len(rows),
            "events_created": events_created,
            "mailboxes_banned": banned,
            "mailboxes_warmed": warmed,
        }

    def _limit_for_day(self, day: int) -> int:
        limits = self.settings.warmup.daily_limits
        if not limits:
            return 5
        idx = min(max(day, 1) - 1, len(limits) - 1)
        return limits[idx]

    async def _get_mailbox(self, mailbox_id: UUID) -> Mailbox:
        mailbox = await self.db.get(Mailbox, mailbox_id)
        if mailbox is None:
            raise NotFoundError(f"Mailbox '{mailbox_id}' not found")
        return mailbox
