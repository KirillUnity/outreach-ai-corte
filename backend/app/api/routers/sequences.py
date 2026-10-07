"""HTTP API for Instantly-shaped sequences (state only, no SMTP)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.sequence import (
    EnrollmentResponse,
    SequenceCreate,
    SequenceEnrollRequest,
    SequenceResponse,
    SequenceTickResponse,
)
from app.services.exceptions import NotFoundError
from app.services.sequence_service import SequenceService

router = APIRouter(prefix="/sequences", tags=["sequences"])


@router.post("/", response_model=SequenceResponse, status_code=status.HTTP_201_CREATED)
async def create_sequence(
    data: SequenceCreate,
    db: AsyncSession = Depends(get_db),
) -> SequenceResponse:
    row = await SequenceService(db).create(data)
    return SequenceResponse.model_validate(row)


@router.get("/", response_model=list[SequenceResponse])
async def list_sequences(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[SequenceResponse]:
    rows = await SequenceService(db).list(limit=limit, offset=offset)
    return [SequenceResponse.model_validate(row) for row in rows]


@router.post("/{sequence_id}/enroll", response_model=EnrollmentResponse)
async def enroll_person(
    sequence_id: UUID,
    data: SequenceEnrollRequest,
    db: AsyncSession = Depends(get_db),
) -> EnrollmentResponse:
    try:
        row = await SequenceService(db).enroll(sequence_id, data.person_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    return EnrollmentResponse.model_validate(row)


@router.post("/{sequence_id}/tick", response_model=SequenceTickResponse)
async def tick_sequence(
    sequence_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SequenceTickResponse:
    service = SequenceService(db)
    try:
        advanced, completed = await service.tick(sequence_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    return SequenceTickResponse(
        sequence_id=sequence_id,
        advanced=advanced,
        completed=completed,
        emails_sent=service.emails_sent,
    )
