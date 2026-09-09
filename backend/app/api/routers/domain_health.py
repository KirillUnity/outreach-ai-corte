"""Domain health / deliverability endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.domain_health import (
    DomainHealthCreate,
    DomainHealthListResponse,
    DomainHealthResponse,
    DomainHealthUpdate,
)
from app.services.domain_health_service import DomainHealthService
from app.services.exceptions import DuplicateError

router = APIRouter(prefix="/deliverability", tags=["deliverability"])


def _service(db: AsyncSession) -> DomainHealthService:
    return DomainHealthService(db)


@router.post(
    "/",
    response_model=DomainHealthResponse,
    summary="Upsert domain health",
)
async def upsert_domain_health(
    data: DomainHealthCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> DomainHealthResponse:
    """Create or replace a snapshot by domain. 201 if created, 200 if updated."""
    row, created = await _service(db).upsert(data)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return DomainHealthResponse.model_validate(row)


@router.get(
    "/",
    response_model=DomainHealthListResponse,
    summary="List domain health",
)
async def list_domain_health(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> DomainHealthListResponse:
    """Return a paginated list of domain health snapshots."""
    items, total = await _service(db).list(limit=limit, offset=offset)
    return DomainHealthListResponse(
        items=[DomainHealthResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{domain}",
    response_model=DomainHealthResponse,
    summary="Get domain health",
)
async def get_domain_health(
    domain: str,
    db: AsyncSession = Depends(get_db),
) -> DomainHealthResponse:
    """Fetch a snapshot by domain."""
    row = await _service(db).get_by_domain(domain)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain health '{domain}' not found",
        )
    return DomainHealthResponse.model_validate(row)


@router.patch(
    "/{domain}",
    response_model=DomainHealthResponse,
    summary="Update domain health",
)
async def update_domain_health(
    domain: str,
    data: DomainHealthUpdate,
    db: AsyncSession = Depends(get_db),
) -> DomainHealthResponse:
    """Partially update a snapshot. Returns 409 if the new domain collides."""
    try:
        row = await _service(db).update(domain, data)
    except DuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from None
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain health '{domain}' not found",
        )
    return DomainHealthResponse.model_validate(row)


@router.delete(
    "/{domain}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete domain health",
)
async def delete_domain_health(
    domain: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a snapshot by domain."""
    deleted = await _service(db).delete(domain)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain health '{domain}' not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
