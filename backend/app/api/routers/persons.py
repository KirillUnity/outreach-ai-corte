"""Person CRUD endpoints."""

import logging
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_email_generator, get_linkedin_service
from app.schemas.company import CompanyResponse
from app.schemas.email_draft import (
    EmailDraftResponse,
    EmailGenerationRequest,
    EmailGenerationResponse,
)
from app.schemas.linkedin import PersonResearchRequest, PersonResearchResponse
from app.schemas.person import (
    PersonCompanyAssign,
    PersonCreate,
    PersonListResponse,
    PersonResponse,
    PersonUpdate,
    PersonWithCompanyResponse,
)
from app.services.company_service import CompanyService
from app.services.email_draft_service import EmailDraftService
from app.services.email_generator import EmailGenerator
from app.services.exceptions import DuplicateError, NotFoundError
from app.services.person_service import PersonService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/persons", tags=["persons"])


def _service(db: AsyncSession) -> PersonService:
    return PersonService(db, linkedin_service=get_linkedin_service())


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


@router.post(
    "/research",
    response_model=PersonResearchResponse,
    summary="Research person from LinkedIn",
)
async def research_person(
    data: PersonResearchRequest,
    db: AsyncSession = Depends(get_db),
) -> PersonResearchResponse:
    """Create or return a cached person from a LinkedIn profile URL."""
    service = _service(db)
    start = time.perf_counter()
    try:
        person, company, source = await service.research_from_linkedin(
            linkedin_url=data.linkedin_url,
            company_domain=data.company_domain,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    except Exception as exc:
        logger.exception("Research failed for %s", data.linkedin_url)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LinkedIn research failed: {exc}",
        ) from None

    duration = time.perf_counter() - start
    return PersonResearchResponse(
        person=PersonResponse.model_validate(person),
        company=CompanyResponse.model_validate(company) if company is not None else None,
        source=source,
        research_duration_seconds=round(duration, 2),
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


@router.post(
    "/{person_id}/generate-email",
    response_model=EmailGenerationResponse,
    summary="Generate a personalized outreach email",
)
async def generate_email_for_person(
    person_id: UUID,
    request: EmailGenerationRequest,
    db: AsyncSession = Depends(get_db),
    email_generator: EmailGenerator = Depends(get_email_generator),
) -> EmailGenerationResponse:
    """RAG context + LLM draft, then persist an EmailDraft. 404 / 400 / 502."""
    if request.person_id != person_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="person_id mismatch",
        )

    person_service = PersonService(db)
    company_service = CompanyService(db)
    draft_service = EmailDraftService(db, email_generator=email_generator)

    start = time.perf_counter()
    try:
        draft, meta = await draft_service.generate_and_save(
            person_id=person_id,
            request=request,
            person_service=person_service,
            company_service=company_service,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None
    except Exception as exc:
        logger.exception("Email generation failed for person %s", person_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Generation failed: {exc}",
        ) from None

    duration = time.perf_counter() - start
    person = await person_service.get_by_id(person_id)
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person '{person_id}' not found",
        )
    company = (
        await company_service.get_by_id(person.company_id) if person.company_id is not None else None
    )
    return EmailGenerationResponse(
        draft=EmailDraftResponse.model_validate(draft),
        person=PersonResponse.model_validate(person),
        company=CompanyResponse.model_validate(company) if company is not None else None,
        rag_context_used=list(meta.get("rag_context_used") or []),
        tokens_input=int(meta.get("tokens_input") or 0),
        tokens_output=int(meta.get("tokens_output") or 0),
        estimated_cost_usd=float(meta.get("estimated_cost_usd") or 0.0),
        model=str(meta.get("model") or ""),
        generation_duration_seconds=round(duration, 2),
    )
