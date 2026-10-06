"""WarmupService helpers with a fake AsyncSession."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.models.mailbox import Mailbox, MailboxStatus
from app.schemas.mailbox import MailboxCreate
from app.services.exceptions import DuplicateError
from app.services.warmup.warmup_service import WarmupService


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Mailbox] = []
        self.existing: Mailbox | None = None
        self.rows: list[Mailbox] = []
        self.timeline_rows: list[tuple[int, int, int, int]] = []
        self.deleted: Mailbox | None = None

    async def execute(self, _stmt: object) -> SimpleNamespace:
        timeline = self.timeline_rows

        class _Scalars:
            def all(self_inner) -> list[Mailbox]:
                return list(self.rows)

        return SimpleNamespace(
            scalar_one_or_none=lambda: self.existing,
            scalar_one=lambda: len(self.rows),
            scalars=lambda: _Scalars(),
            all=lambda: timeline,
        )

    def add(self, row: Mailbox) -> None:
        if getattr(row, "id", None) is None:
            row.id = uuid4()
        self.added.append(row)

    async def commit(self) -> None:
        return None

    async def refresh(self, row: Mailbox) -> None:
        from datetime import datetime, timezone

        if getattr(row, "created_at", None) is None:
            row.created_at = datetime.now(timezone.utc)
        row.updated_at = row.created_at

    async def get(self, _model: object, pk: object) -> Mailbox | None:
        for row in self.rows:
            if row.id == pk:
                return row
        if self.existing and self.existing.id == pk:
            return self.existing
        return None

    async def delete(self, row: Mailbox) -> None:
        self.deleted = row


@pytest.mark.asyncio
async def test_create_mailbox_extracts_domain() -> None:
    db = FakeSession()
    service = WarmupService(db, Settings())
    row = await service.create_mailbox(MailboxCreate(email="Kirill@Mail.Yourdomain.com", display_name="K"))
    assert row.email == "kirill@mail.yourdomain.com"
    assert row.domain == "mail.yourdomain.com"
    assert row.status == MailboxStatus.NEW
    assert row.reputation_score == 50.0


@pytest.mark.asyncio
async def test_create_duplicate_email_raises() -> None:
    db = FakeSession()
    db.existing = Mailbox(email="a@b.com", domain="b.com")
    db.existing.id = uuid4()
    service = WarmupService(db, Settings())
    with pytest.raises(DuplicateError):
        await service.create_mailbox(MailboxCreate(email="a@b.com"))


@pytest.mark.asyncio
async def test_list_mailboxes_filter_by_status() -> None:
    warming = Mailbox(email="w@ex.com", domain="ex.com")
    warming.id = uuid4()
    warming.status = MailboxStatus.WARMING
    db = FakeSession()
    db.rows = [warming]
    service = WarmupService(db, Settings())
    items, total = await service.list_mailboxes(status=MailboxStatus.WARMING)
    assert total == 1
    assert items[0].status == MailboxStatus.WARMING


@pytest.mark.asyncio
async def test_get_timeline_aggregates_events() -> None:
    mailbox = Mailbox(email="w@ex.com", domain="ex.com")
    mailbox.id = uuid4()
    db = FakeSession()
    db.existing = mailbox
    db.timeline_rows = [(1, 5, 4, 1), (2, 10, 7, 2)]
    service = WarmupService(db, Settings())
    points = await service.get_timeline(mailbox.id)
    assert points[0].day == 1
    assert points[0].sent == 5
    assert points[0].opened == 4
    assert points[1].replied == 2
