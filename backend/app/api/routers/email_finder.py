"""HTTP API for email discovery."""

from __future__ import annotations

import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_settings
from app.core.config import Settings
from app.schemas.email_candidate import (
    EmailCandidateResponse,
    EmailFindRequest,
    EmailFindResponse,
)
from app.services.exceptions import NotFoundError
from app.services.email_finder.finder import EmailFinder
from app.services.person_service import PersonService

router = APIRouter(prefix="/email", tags=["email-finder"])


def _finder(db: AsyncSession, settings: Settings) -> EmailFinder:
    return EmailFinder(db, settings)


@router.post("/find", response_model=EmailFindResponse)
async def find_email(
    data: EmailFindRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EmailFindResponse:
    person = await PersonService(db).get_by_id(data.person_id)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    started = time.perf_counter()
    finder = _finder(db, settings)
    rows = await finder.find_for_person(
        person,
        domain=data.domain,
        use_hunter=data.use_hunter,
        use_apollo=data.use_apollo,
        use_smtp=data.use_smtp,
    )
    if data.prefer_source is not None:
        preferred = [row for row in rows if row.source == data.prefer_source]
        rest = [row for row in rows if row.source != data.prefer_source]
        rows = preferred + rest
    primary = next((row for row in rows if row.is_primary), rows[0] if rows else None)
    sources = sorted({row.source.value for row in rows})
    return EmailFindResponse(
        person_id=data.person_id,
        candidates=[EmailCandidateResponse.model_validate(row) for row in rows],
        primary_email=primary.email if primary else None,
        best_confidence=max((row.confidence for row in rows), default=0.0),
        sources_used=sources,
        duration_seconds=round(time.perf_counter() - started, 3),
    )


@router.get("/candidates/{person_id}", response_model=list[EmailCandidateResponse])
async def list_candidates(
    person_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[EmailCandidateResponse]:
    person = await PersonService(db).get_by_id(person_id)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    rows = await _finder(db, settings).get_candidates(person_id)
    return [EmailCandidateResponse.model_validate(row) for row in rows]


@router.post("/candidates/{candidate_id}/set-primary", response_model=EmailCandidateResponse)
async def set_primary(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EmailCandidateResponse:
    try:
        row = await _finder(db, settings).set_primary(candidate_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    return EmailCandidateResponse.model_validate(row)


@router.post("/candidates/{candidate_id}/verify", response_model=EmailCandidateResponse)
async def verify_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EmailCandidateResponse:
    try:
        row = await _finder(db, settings).verify_existing(candidate_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    return EmailCandidateResponse.model_validate(row)


@router.delete("/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    deleted = await _finder(db, settings).delete_candidate(candidate_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
