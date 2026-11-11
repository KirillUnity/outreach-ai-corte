"""Outbound attempt rows for a mocked Hunter 429. No vendor socket is opened."""

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.outbound_attempt import OutboundAttempt
from app.schemas.outbound_attempt import OutboundAttemptResponse
from app.services.email_finder.hunter_client import HunterClient
from app.services.outbound_attempts import (
    hunter_email_target,
    list_attempts,
    lookup_hunter_email,
)

_NOW = datetime(2026, 11, 11, 8, 0, tzinfo=timezone.utc)
_LATER = datetime(2026, 11, 11, 8, 5, tzinfo=timezone.utc)


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        email_finder=SimpleNamespace(
            hunter_enabled=True,
            hunter_api_key="test-key",
            hunter_base_url="https://api.hunter.io/v2",
        )
    )


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(OutboundAttempt.__table__.create)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        yield session
    await engine.dispose()


def _client(
    handler: object,
) -> tuple[httpx.AsyncClient, HunterClient]:
    transport = httpx.MockTransport(handler)  # type: ignore[arg-type]
    http = httpx.AsyncClient(transport=transport)
    return http, HunterClient(_settings(), client=http)  # type: ignore[arg-type]


async def _lookup(
    db: AsyncSession,
    hunter: HunterClient,
    now: datetime,
) -> list[dict]:
    return await lookup_hunter_email(
        db,
        hunter,
        first_name="Ada",
        last_name="Lovelace",
        domain="acme.com",
        now=now,
    )


@pytest.mark.asyncio
async def test_rate_limit_records_failed_attempt(db: AsyncSession) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.hunter.io"
        return httpx.Response(429, text="too many requests")

    http, hunter = _client(handler)
    hits = await _lookup(db, hunter, _NOW)
    await http.aclose()

    assert hits == []
    rows = await list_attempts(db)
    assert len(rows) == 1
    row = rows[0]
    assert row.target == hunter_email_target("acme.com", "Ada", "Lovelace")
    assert row.status == "failed"
    assert row.attempt_count > 0
    assert row.last_error is not None and "429" in row.last_error
    assert row.next_attempt_at is not None
    assert row.next_attempt_at > _NOW

    visible = OutboundAttemptResponse.model_validate(row)
    assert visible.attempt_count == row.attempt_count
    assert visible.last_error == row.last_error
    assert visible.next_attempt_at == row.next_attempt_at
    assert visible.status == "failed"
    assert visible.target == row.target


@pytest.mark.asyncio
async def test_second_rate_limit_updates_same_row(db: AsyncSession) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="too many requests")

    http, hunter = _client(handler)
    await _lookup(db, hunter, _NOW)
    first = (await list_attempts(db))[0]
    first_id = first.id
    first_count = first.attempt_count
    await _lookup(db, hunter, _LATER)
    await http.aclose()

    rows = await list_attempts(db)
    assert len(rows) == 1
    row = rows[0]
    assert row.id == first_id
    assert row.attempt_count == first_count + 1
    assert row.status == "failed"
    assert row.last_error is not None and "429" in row.last_error
    assert row.next_attempt_at is not None and row.next_attempt_at > _LATER
    assert all(item.status != "succeeded" for item in rows)


@pytest.mark.asyncio
async def test_success_on_first_try(db: AsyncSession) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": {"email": "ada@acme.com", "score": 90, "sources": []}},
        )

    http, hunter = _client(handler)
    hits = await _lookup(db, hunter, _NOW)
    await http.aclose()

    assert hits[0]["email"] == "ada@acme.com"
    rows = await list_attempts(db)
    assert len(rows) == 1
    row = rows[0]
    assert row.status == "succeeded"
    assert row.attempt_count == 1
    assert not row.last_error


@pytest.mark.asyncio
async def test_success_after_failure_keeps_history(db: AsyncSession) -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, text="too many requests")
        return httpx.Response(
            200,
            json={"data": {"email": "ada@acme.com", "score": 80, "sources": []}},
        )

    http, hunter = _client(handler)
    assert await _lookup(db, hunter, _NOW) == []
    failed = (await list_attempts(db))[0]
    assert failed.status == "failed"
    failed_id = failed.id
    failed_count = failed.attempt_count
    hits = await _lookup(db, hunter, _LATER)
    await http.aclose()

    assert hits[0]["email"] == "ada@acme.com"
    rows = await list_attempts(db)
    assert len(rows) == 1
    row = rows[0]
    assert row.id == failed_id
    assert row.status == "succeeded"
    assert row.attempt_count == failed_count + 1
    assert row.last_error is not None and "429" in row.last_error
