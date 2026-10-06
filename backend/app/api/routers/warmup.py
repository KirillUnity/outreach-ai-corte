"""Warmup mailbox HTTP API."""

from __future__ import annotations

import time
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_settings
from app.core.config import Settings
from app.models.mailbox import MailboxStatus
from app.schemas.mailbox import (
    MailboxCreate,
    MailboxListResponse,
    MailboxResponse,
    MailboxStatsResponse,
    WarmupEventResponse,
    WarmupMailboxTickResponse,
    WarmupStartRequest,
    WarmupTickResponse,
    WarmupTimelinePoint,
)
from app.services.exceptions import DuplicateError, NotFoundError
from app.services.warmup.warmup_emulator import WarmupEmulator
from app.services.warmup.warmup_service import WarmupService

router = APIRouter(prefix="/warmup", tags=["warmup"])


def _service(db: AsyncSession, settings: Settings) -> WarmupService:
    return WarmupService(db, settings)


def _require_ops_token(settings: Settings, x_admin_token: str | None) -> None:
    token = settings.graph_sync_token
    allowed = (token and x_admin_token == token) or (settings.debug and not token)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin token required")


@router.post("/mailboxes", response_model=MailboxResponse, status_code=status.HTTP_201_CREATED)
async def create_mailbox(
    data: MailboxCreate,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MailboxResponse:
    try:
        row = await _service(db, settings).create_mailbox(data)
    except DuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from None
    return MailboxResponse.from_mailbox(row)


@router.get("/mailboxes", response_model=MailboxListResponse)
async def list_mailboxes(
    status_filter: MailboxStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MailboxListResponse:
    items, total = await _service(db, settings).list_mailboxes(
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return MailboxListResponse(
        items=[MailboxResponse.from_mailbox(row) for row in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/tick-all", response_model=WarmupTickResponse)
async def tick_all_mailboxes(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> WarmupTickResponse:
    """One simulated day for every WARMING mailbox. n8n Cron should call this hourly."""
    _require_ops_token(settings, x_admin_token)
    emulator = WarmupEmulator(db, settings)
    started = time.perf_counter()
    result = await emulator.tick_all()
    result["duration_seconds"] = round(time.perf_counter() - started, 2)
    return WarmupTickResponse(**result)


@router.post("/start")
async def start_many(
    body: WarmupStartRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[MailboxResponse]:
    service = _service(db, settings)
    ids = body.mailbox_ids
    if ids is None:
        rows, _ = await service.list_mailboxes(status=MailboxStatus.NEW, limit=100, offset=0)
        ids = [row.id for row in rows]
    started: list[MailboxResponse] = []
    for mailbox_id in ids:
        row = await service.start_warmup(mailbox_id, reset=body.reset_progress)
        started.append(MailboxResponse.from_mailbox(row))
    return started


@router.get("/mailboxes/{mailbox_id}", response_model=MailboxResponse)
async def get_mailbox(
    mailbox_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MailboxResponse:
    row = await _service(db, settings).get_mailbox(mailbox_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mailbox '{mailbox_id}' not found")
    return MailboxResponse.from_mailbox(row)


@router.delete("/mailboxes/{mailbox_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mailbox(
    mailbox_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    deleted = await _service(db, settings).delete_mailbox(mailbox_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mailbox '{mailbox_id}' not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/mailboxes/{mailbox_id}/start", response_model=MailboxResponse)
async def start_warmup(
    mailbox_id: UUID,
    reset: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MailboxResponse:
    try:
        row = await _service(db, settings).start_warmup(mailbox_id, reset=reset)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    return MailboxResponse.from_mailbox(row)


@router.post("/mailboxes/{mailbox_id}/pause", response_model=MailboxResponse)
async def pause_mailbox(
    mailbox_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MailboxResponse:
    try:
        row = await _service(db, settings).pause_mailbox(mailbox_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    return MailboxResponse.from_mailbox(row)


@router.post("/mailboxes/{mailbox_id}/resume", response_model=MailboxResponse)
async def resume_mailbox(
    mailbox_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MailboxResponse:
    service = _service(db, settings)
    existing = await service.get_mailbox(mailbox_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mailbox '{mailbox_id}' not found")
    if existing.status == MailboxStatus.BANNED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot resume a banned mailbox")
    row = await service.resume_mailbox(mailbox_id)
    return MailboxResponse.from_mailbox(row)


@router.post("/mailboxes/{mailbox_id}/tick", response_model=WarmupMailboxTickResponse)
async def tick_mailbox(
    mailbox_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> WarmupMailboxTickResponse:
    try:
        result = await _service(db, settings).run_tick(mailbox_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    return WarmupMailboxTickResponse(**result)


@router.get("/mailboxes/{mailbox_id}/stats", response_model=MailboxStatsResponse)
async def mailbox_stats(
    mailbox_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MailboxStatsResponse:
    try:
        return await _service(db, settings).get_stats(mailbox_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None


@router.get("/mailboxes/{mailbox_id}/events", response_model=list[WarmupEventResponse])
async def mailbox_events(
    mailbox_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[WarmupEventResponse]:
    try:
        rows = await _service(db, settings).get_events(mailbox_id, limit=limit)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    return [WarmupEventResponse.model_validate(row) for row in rows]


@router.get("/mailboxes/{mailbox_id}/timeline", response_model=list[WarmupTimelinePoint])
async def mailbox_timeline(
    mailbox_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[WarmupTimelinePoint]:
    try:
        return await _service(db, settings).get_timeline(mailbox_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
