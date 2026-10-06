"""WarmupEmulator — fake session, no Postgres, no SMTP."""

from __future__ import annotations

import random
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import Settings, WarmupSettings
from app.models.mailbox import Mailbox, MailboxStatus
from app.models.warmup_event import WarmupEventType
from app.services.exceptions import NotFoundError
from app.services.warmup.warmup_emulator import WarmupEmulator


class FakeSession:
    def __init__(self, mailbox: Mailbox | None) -> None:
        self.mailbox = mailbox
        self.added: list[object] = []
        self.warming: list[Mailbox] = []

    async def get(self, _model: object, pk: object) -> Mailbox | None:
        if self.mailbox is not None and self.mailbox.id == pk:
            return self.mailbox
        return None

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        return None

    async def refresh(self, _obj: object) -> None:
        return None

    async def execute(self, _stmt: object) -> SimpleNamespace:
        rows = self.warming or ([self.mailbox] if self.mailbox and self.mailbox.status == MailboxStatus.WARMING else [])

        class _Scalars:
            def all(self_inner) -> list[Mailbox]:
                return rows

        return SimpleNamespace(scalars=lambda: _Scalars())


def _mailbox(**kwargs: object) -> Mailbox:
    row = Mailbox(
        email=str(kwargs.pop("email", "sender@example.com")),
        domain=str(kwargs.pop("domain", "example.com")),
    )
    row.id = uuid4()
    for key, value in kwargs.items():
        setattr(row, key, value)
    return row


def _settings(**kwargs: object) -> Settings:
    return Settings(warmup=WarmupSettings(max_emails_per_tick=50, rng_seed=42, **kwargs))


def _emulator(mailbox: Mailbox | None, settings: Settings | None = None) -> WarmupEmulator:
    db = FakeSession(mailbox)
    emu = WarmupEmulator(db, settings or _settings(), rng=random.Random(42))
    emu._fake_db = db  # type: ignore[attr-defined]
    return emu


@pytest.mark.asyncio
async def test_start_warmup_sets_status_warming() -> None:
    mailbox = _mailbox(status=MailboxStatus.NEW, warmup_day=0)
    emu = _emulator(mailbox)
    out = await emu.start_warmup(mailbox.id)
    assert out.status == MailboxStatus.WARMING
    assert out.warmup_day == 1
    assert out.daily_limit == 5


@pytest.mark.asyncio
async def test_start_warmup_reset_clears_stats() -> None:
    mailbox = _mailbox(
        status=MailboxStatus.WARMED,
        warmup_day=12,
        total_sent=40,
        total_opened=20,
        reputation_score=80.0,
    )
    emu = _emulator(mailbox)
    out = await emu.start_warmup(mailbox.id, reset=True)
    assert out.total_sent == 0
    assert out.total_opened == 0
    assert out.reputation_score == 50.0
    assert out.warmup_day == 1
    assert out.status == MailboxStatus.WARMING


@pytest.mark.asyncio
async def test_tick_creates_events() -> None:
    mailbox = _mailbox(status=MailboxStatus.WARMING, warmup_day=1, daily_limit=5)
    emu = _emulator(
        mailbox,
        _settings(
            peer_open_rate=0.0,
            peer_reply_rate=0.0,
            peer_spam_rate=0.0,
            peer_bounce_rate=0.0,
            peer_important_rate=0.0,
        ),
    )
    created = await emu.tick(mailbox.id)
    sent = [e for e in emu._fake_db.added if getattr(e, "event_type", None) == WarmupEventType.SENT]  # type: ignore[attr-defined]
    assert created == 5
    assert len(sent) == 5
    assert mailbox.total_sent == 5


@pytest.mark.asyncio
async def test_tick_increments_warmup_day() -> None:
    mailbox = _mailbox(status=MailboxStatus.WARMING, warmup_day=1)
    emu = _emulator(
        mailbox,
        _settings(
            peer_open_rate=0.0,
            peer_reply_rate=0.0,
            peer_spam_rate=0.0,
            peer_bounce_rate=0.0,
            peer_important_rate=0.0,
        ),
    )
    await emu.tick(mailbox.id)
    assert mailbox.warmup_day == 2


@pytest.mark.asyncio
async def test_tick_updates_daily_limit() -> None:
    mailbox = _mailbox(status=MailboxStatus.WARMING, warmup_day=7, daily_limit=5)
    emu = _emulator(
        mailbox,
        _settings(
            peer_open_rate=0.0,
            peer_reply_rate=0.0,
            peer_spam_rate=0.0,
            peer_bounce_rate=0.0,
            peer_important_rate=0.0,
        ),
    )
    await emu.tick(mailbox.id)
    assert mailbox.warmup_day == 8
    assert mailbox.daily_limit == 10

    mailbox.warmup_day = 14
    await emu.tick(mailbox.id)
    assert mailbox.warmup_day == 15
    assert mailbox.daily_limit == 20


def test_reputation_compute_high_open() -> None:
    mailbox = _mailbox(total_sent=100, total_opened=90, total_replied=15, total_bounced=0, total_spam_reports=0)
    emu = _emulator(mailbox)
    score = emu._compute_reputation(mailbox)
    assert score > 70


def test_reputation_compute_high_bounce() -> None:
    mailbox = _mailbox(total_sent=100, total_opened=0, total_replied=0, total_bounced=10, total_spam_reports=0)
    emu = _emulator(mailbox)
    score = emu._compute_reputation(mailbox)
    assert score < 30


@pytest.mark.asyncio
async def test_tick_bans_mailbox_on_low_reputation() -> None:
    mailbox = _mailbox(status=MailboxStatus.WARMING, warmup_day=1)
    emu = _emulator(
        mailbox,
        _settings(
            peer_open_rate=0.0,
            peer_reply_rate=0.0,
            peer_spam_rate=1.0,
            peer_bounce_rate=0.0,
            peer_important_rate=0.0,
            reputation_ban_threshold=20.0,
        ),
    )
    await emu.tick(mailbox.id)
    assert mailbox.status == MailboxStatus.BANNED
    assert mailbox.reputation_score < 20


@pytest.mark.asyncio
async def test_tick_marks_warmed_after_30_days() -> None:
    mailbox = _mailbox(
        status=MailboxStatus.WARMING,
        warmup_day=29,
        total_sent=200,
        total_opened=180,
        total_replied=40,
        total_bounced=0,
        total_spam_reports=0,
        reputation_score=80.0,
    )
    emu = _emulator(
        mailbox,
        _settings(
            peer_open_rate=1.0,
            peer_reply_rate=0.2,
            peer_spam_rate=0.0,
            peer_bounce_rate=0.0,
            peer_important_rate=0.0,
        ),
    )
    await emu.tick(mailbox.id)
    assert mailbox.warmup_day >= 30
    assert mailbox.status == MailboxStatus.WARMED


@pytest.mark.asyncio
async def test_tick_paused_mailbox_returns_zero() -> None:
    mailbox = _mailbox(status=MailboxStatus.PAUSED, warmup_day=3)
    emu = _emulator(mailbox)
    created = await emu.tick(mailbox.id)
    assert created == 0
    assert emu._fake_db.added == []  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_tick_missing_mailbox() -> None:
    emu = _emulator(None)
    with pytest.raises(NotFoundError):
        await emu.tick(uuid4())
