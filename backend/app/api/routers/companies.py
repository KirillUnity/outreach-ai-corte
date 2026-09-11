"""Company CRUD endpoints."""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.company import (
    CompanyCreate,
    CompanyListResponse,
    CompanyResearchResponse,
    CompanyResponse,
    CompanyUpdate,
)
from app.services.company_service import CompanyService
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["companies"])


def _service(db: AsyncSession) -> CompanyService:
    return CompanyService(db)


@router.post(
    "/",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create company",
)
async def create_company(
    data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    """Create a company. Returns 409 if the domain is already registered."""
    service = _service(db)
    existing = await service.get_by_domain(data.domain)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Company with domain '{data.domain}' already exists",
        )
    try:
        company = await service.create(data)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Company with domain '{data.domain}' already exists",
        ) from None
    return CompanyResponse.model_validate(company)


@router.get(
    "/",
    response_model=CompanyListResponse,
    summary="List companies",
)
async def list_companies(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> CompanyListResponse:
    """Return a paginated list of companies."""
    items, total = await _service(db).list(limit=limit, offset=offset)
    return CompanyListResponse(
        items=[CompanyResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{domain}",
    response_model=CompanyResponse,
    summary="Get company by domain",
)
async def get_company(
    domain: str,
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    """Fetch a single company by domain."""
    company = await _service(db).get_by_domain(domain)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company '{domain}' not found",
        )
    return CompanyResponse.model_validate(company)


@router.post(
    "/{domain}/research",
    response_model=CompanyResearchResponse,
    summary="Research company website",
)
async def research_company(
    domain: str,
    db: AsyncSession = Depends(get_db),
) -> CompanyResearchResponse:
    """Parse the company site and store raw_site_text for later RAG."""
    service = _service(db)
    existing = await service.get_by_domain(domain)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company '{domain}' not found",
        )

    start = time.perf_counter()
    try:
        company, parsed = await service.research(domain)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    except Exception as exc:
        logger.exception("Research failed for %s", domain)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Research failed: {exc}",
        ) from None

    duration = time.perf_counter() - start
    return CompanyResearchResponse(
        company=CompanyResponse.model_validate(company),
        pages_parsed=parsed.pages_parsed,
        errors=parsed.errors,
        research_duration_seconds=round(duration, 2),
    )


@router.patch(
    "/{domain}",
    response_model=CompanyResponse,
    summary="Update company",
)
async def update_company(
    domain: str,
    data: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    """Partially update a company. Returns 409 if the new domain collides."""
    try:
        company = await _service(db).update(domain, data)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company domain already exists",
        ) from None
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company '{domain}' not found",
        )
    return CompanyResponse.model_validate(company)


@router.delete(
    "/{domain}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete company",
)
async def delete_company(
    domain: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a company. Related persons keep their rows (company_id SET NULL)."""
    deleted = await _service(db).delete(domain)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company '{domain}' not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
