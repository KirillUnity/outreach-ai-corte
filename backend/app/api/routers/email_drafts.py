"""Email draft CRUD endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.email_draft import (
    EmailDraftCreate,
    EmailDraftListResponse,
    EmailDraftResponse,
    EmailDraftUpdate,
    EmailDraftWithPersonResponse,
)
from app.services.email_draft_service import EmailDraftService
from app.services.exceptions import NotFoundError

router = APIRouter(prefix="/email-drafts", tags=["email-drafts"])


def _service(db: AsyncSession) -> EmailDraftService:
    return EmailDraftService(db)


@router.post(
    "/",
    response_model=EmailDraftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create email draft",
)
async def create_email_draft(
    data: EmailDraftCreate,
    db: AsyncSession = Depends(get_db),
) -> EmailDraftResponse:
    """Create a draft. Returns 404 if person_id does not exist."""
    try:
        draft = await _service(db).create(data)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    return EmailDraftResponse.model_validate(draft)


@router.get(
    "/",
    response_model=EmailDraftListResponse,
    summary="List email drafts",
)
async def list_email_drafts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    person_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> EmailDraftListResponse:
    """Return a paginated list, optionally filtered by person_id."""
    items, total = await _service(db).list(limit=limit, offset=offset, person_id=person_id)
    return EmailDraftListResponse(
        items=[EmailDraftResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{draft_id}",
    response_model=EmailDraftWithPersonResponse,
    summary="Get email draft with person",
)
async def get_email_draft(
    draft_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> EmailDraftWithPersonResponse:
    """Fetch a draft and eagerly load the related person."""
    draft = await _service(db).get_with_person(draft_id)
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email draft '{draft_id}' not found",
        )
    return EmailDraftWithPersonResponse.model_validate(draft)


@router.patch(
    "/{draft_id}",
    response_model=EmailDraftResponse,
    summary="Update email draft",
)
async def update_email_draft(
    draft_id: UUID,
    data: EmailDraftUpdate,
    db: AsyncSession = Depends(get_db),
) -> EmailDraftResponse:
    """Partially update a draft."""
    try:
        draft = await _service(db).update(draft_id, data)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email draft '{draft_id}' not found",
        )
    return EmailDraftResponse.model_validate(draft)


@router.delete(
    "/{draft_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete email draft",
)
async def delete_email_draft(
    draft_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a draft."""
    deleted = await _service(db).delete(draft_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email draft '{draft_id}' not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{draft_id}/mark-sent",
    response_model=EmailDraftResponse,
    summary="Mark draft as sent",
)
async def mark_email_draft_sent(
    draft_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> EmailDraftResponse:
    """Set is_sent=true and sent_at to now (UTC)."""
    draft = await _service(db).mark_sent(draft_id)
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email draft '{draft_id}' not found",
        )
    return EmailDraftResponse.model_validate(draft)
