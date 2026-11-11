"""Persist one outbound-attempt row per target. Repeats update that row."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbound_attempt import STATUS_FAILED, STATUS_SUCCEEDED, OutboundAttempt
from app.services.email_finder.hunter_client import HunterClient

_RETRY_SECONDS = 60


def hunter_email_target(domain: str, first_name: str, last_name: str) -> str:
    """Stable id for one Hunter email-finder call."""
    return (
        f"hunter:email-finder:{domain.strip().lower()}:"
        f"{first_name.strip().lower()}:{last_name.strip().lower()}"
    )


def _as_utc(now: datetime) -> datetime:
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _format_error(status_code: int, error: str) -> str:
    detail = error.strip()
    code = str(status_code)
    if code in detail:
        return detail
    if detail:
        return f"{code} {detail}"
    return code


def _next_attempt_at(now: datetime, attempt_count: int) -> datetime:
    delay_seconds = max(_RETRY_SECONDS, _RETRY_SECONDS * attempt_count)
    scheduled = now + timedelta(seconds=delay_seconds)
    if scheduled <= now:
        scheduled = now + timedelta(seconds=1)
    return scheduled


async def get_by_target(db: AsyncSession, target: str) -> OutboundAttempt | None:
    """Return the attempt row for `target`, if one was stored."""
    stmt = select(OutboundAttempt).where(OutboundAttempt.target == target)
    return (await db.execute(stmt)).scalar_one_or_none()


async def record_failure(
    db: AsyncSession,
    target: str,
    status_code: int,
    error: str,
    now: datetime,
) -> OutboundAttempt:
    """Increment the same target row, keep status failed, and schedule a later retry.

    A repeated failure updates this row. It does not insert a succeeded row.
    """
    moment = _as_utc(now)
    row = await get_by_target(db, target)
    if row is None:
        row = OutboundAttempt(
            target=target,
            attempt_count=0,
            last_error=None,
            next_attempt_at=None,
            status=STATUS_FAILED,
        )
        db.add(row)
    row.attempt_count += 1
    row.last_error = _format_error(status_code, error)
    row.next_attempt_at = _next_attempt_at(moment, row.attempt_count)
    row.status = STATUS_FAILED
    row.updated_at = moment
    await db.flush()
    return row


async def record_success(db: AsyncSession, target: str, now: datetime) -> OutboundAttempt:
    """Mark the target succeeded only after a real success.

    A first success stores attempt_count 1 and an empty last_error.
    A success after failures keeps the previous count readable by incrementing
    it and leaves last_error in place.
    """
    moment = _as_utc(now)
    row = await get_by_target(db, target)
    if row is None:
        row = OutboundAttempt(
            target=target,
            attempt_count=1,
            last_error=None,
            next_attempt_at=None,
            status=STATUS_SUCCEEDED,
            updated_at=moment,
        )
        db.add(row)
    else:
        row.attempt_count += 1
        row.status = STATUS_SUCCEEDED
        row.updated_at = moment
    await db.flush()
    return row


async def list_attempts(db: AsyncSession) -> list[OutboundAttempt]:
    """Return every stored attempt, stable by target."""
    stmt = select(OutboundAttempt).order_by(OutboundAttempt.target.asc())
    return list((await db.execute(stmt)).scalars().all())


async def lookup_hunter_email(
    db: AsyncSession,
    hunter: HunterClient,
    *,
    first_name: str,
    last_name: str,
    domain: str,
    now: datetime,
) -> list[dict[str, Any]]:
    """Call Hunter and write 429 or a real success onto one attempt row.

    Hunter itself does not touch SQL. A 429 still yields no email address.
    Disabled Hunter stays a silent empty list and is not recorded.
    """
    if not hunter.enabled:
        return []
    hits = await hunter.find_email(first_name, last_name, domain)
    target = hunter_email_target(domain, first_name, last_name)
    outcome = hunter.last_outcome
    if outcome.rate_limited:
        await record_failure(
            db,
            target,
            outcome.status_code or 429,
            outcome.error or "too many requests",
            now,
        )
        return []
    if outcome.status_code is not None and 200 <= outcome.status_code < 300:
        await record_success(db, target, now)
    return hits
