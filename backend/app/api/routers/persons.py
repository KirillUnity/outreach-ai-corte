"""Person CRUD endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.person import (
    PersonCompanyAssign,
    PersonCreate,
    PersonListResponse,
    PersonResponse,
    PersonUpdate,
    PersonWithCompanyResponse,
)
from app.services.exceptions import DuplicateError, NotFoundError
from app.services.person_service import PersonService

router = APIRouter(prefix="/persons", tags=["persons"])


def _service(db: AsyncSession) -> PersonService:
    return PersonService(db)


@router.post(
    "/",
    response_model=PersonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create person",
)
async def create_person(
    data: PersonCreate,
    db: AsyncSession = Depends(get_db),
) -> PersonResponse:
    """Create a person. 409 on duplicate linkedin_url/email, 404 if company_id is unknown."""
    try:
        person = await _service(db).create(data)
    except DuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from None
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    return PersonResponse.model_validate(person)


@router.get(
    "/",
    response_model=PersonListResponse,
    summary="List persons",
)
async def list_persons(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    company_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> PersonListResponse:
    """Return a paginated list, optionally filtered by company_id."""
    items, total = await _service(db).list(limit=limit, offset=offset, company_id=company_id)
    return PersonListResponse(
        items=[PersonResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{person_id}",
    response_model=PersonWithCompanyResponse,
    summary="Get person with company",
)
async def get_person(
    person_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PersonWithCompanyResponse:
    """Fetch a person and eagerly load the related company."""
    person = await _service(db).get_with_company(person_id)
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person '{person_id}' not found",
        )
    return PersonWithCompanyResponse.model_validate(person)


@router.patch(
    "/{person_id}",
    response_model=PersonResponse,
    summary="Update person",
)
async def update_person(
    person_id: UUID,
    data: PersonUpdate,
    db: AsyncSession = Depends(get_db),
) -> PersonResponse:
    """Partially update a person."""
    try:
        person = await _service(db).update(person_id, data)
    except DuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from None
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person '{person_id}' not found",
        )
    return PersonResponse.model_validate(person)


@router.delete(
    "/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete person",
)
async def delete_person(
    person_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a person. Related email drafts are removed by CASCADE."""
    deleted = await _service(db).delete(person_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person '{person_id}' not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{person_id}/company",
    response_model=PersonResponse,
    summary="Assign person to company",
)
async def assign_company(
    person_id: UUID,
    data: PersonCompanyAssign,
    db: AsyncSession = Depends(get_db),
) -> PersonResponse:
    """Bind an existing person to an existing company."""
    try:
        person = await _service(db).set_company(person_id, data.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person '{person_id}' not found",
        )
    return PersonResponse.model_validate(person)
