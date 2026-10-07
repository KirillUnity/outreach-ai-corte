"""People-search enrichment (Phantombuster mock/real). Does not scrape LinkedIn."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_linkedin_service
from app.schemas.company import CompanyResponse, normalize_domain
from app.schemas.linkedin import LinkedInProfile
from app.schemas.person import PersonResponse
from app.services.exceptions import DuplicateError, NotFoundError
from app.services.linkedin_service import LinkedInService
from app.services.person_service import PersonService

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


class PeopleSearchRequest(BaseModel):
    company_domain: str
    title_contains: str | None = None
    limit: int = Field(default=10, ge=1, le=25)

    @field_validator("company_domain")
    @classmethod
    def _domain(cls, value: str) -> str:
        return normalize_domain(value)


class PeopleSearchHit(BaseModel):
    person: PersonResponse
    profile: LinkedInProfile
    created: bool


class PeopleSearchResponse(BaseModel):
    company: CompanyResponse | None = None
    hits: list[PeopleSearchHit]
    source: str
    count: int


@router.post("/people-search", response_model=PeopleSearchResponse)
async def people_search(
    data: PeopleSearchRequest,
    db: AsyncSession = Depends(get_db),
    linkedin: LinkedInService = Depends(get_linkedin_service),
) -> PeopleSearchResponse:
    profiles = await linkedin.search_people(
        data.company_domain,
        title_contains=data.title_contains,
        limit=data.limit,
    )
    service = PersonService(db, linkedin_service=linkedin)
    try:
        rows, company = await service.ingest_search_profiles(profiles, data.company_domain)
    except (DuplicateError, NotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc.detail)) from None
    by_url = {person.linkedin_url: (person, was_new) for person, was_new in rows if person.linkedin_url}
    hits: list[PeopleSearchHit] = []
    for profile in profiles:
        packed = by_url.get(profile.linkedin_url)
        if packed is None:
            continue
        person, was_new = packed
        hits.append(
            PeopleSearchHit(
                person=PersonResponse.model_validate(person),
                profile=profile,
                created=was_new,
            )
        )
    source = profiles[0].source if profiles else "mock"
    return PeopleSearchResponse(
        company=CompanyResponse.model_validate(company) if company is not None else None,
        hits=hits,
        source=source,
        count=len(hits),
    )
