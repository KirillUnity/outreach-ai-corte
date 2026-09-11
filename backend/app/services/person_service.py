"""Person business logic (CRUD + company binding)."""

import logging
import re
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.company import Company
from app.models.enums import EmailStatus
from app.models.person import Person
from app.schemas.company import CompanyCreate
from app.schemas.person import PersonCreate, PersonUpdate, normalize_linkedin_url
from app.services.company_service import CompanyService
from app.services.exceptions import DuplicateError, NotFoundError
from app.services.linkedin_service import LinkedInService

logger = logging.getLogger(__name__)


class PersonService:
    """CRUD operations for `Person` using an injected async session."""

    def __init__(self, db: AsyncSession, linkedin_service: LinkedInService | None = None) -> None:
        self.db = db
        self._linkedin_service = linkedin_service

    @property
    def linkedin_service(self) -> LinkedInService:
        """Lazy default so tests can inject a fake LinkedIn adapter."""
        if self._linkedin_service is None:
            self._linkedin_service = LinkedInService(settings)
        return self._linkedin_service

    async def create(self, data: PersonCreate) -> Person:
        """Insert a person. Validates company_id and unique linkedin_url / email."""
        await self._assert_unique(linkedin_url=data.linkedin_url, email=data.email)
        if data.company_id is not None:
            await self._require_company(data.company_id)

        payload = data.model_dump()
        if payload.get("email_status") is None:
            payload["email_status"] = EmailStatus.UNKNOWN

        person = Person(**payload)
        self.db.add(person)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise DuplicateError("Person with this linkedin_url already exists") from None
        await self.db.refresh(person)
        return person

    async def get_by_id(self, person_id: UUID) -> Person | None:
        """Return a person by primary key, or None."""
        result = await self.db.execute(select(Person).where(Person.id == person_id))
        return result.scalar_one_or_none()

    async def get_by_linkedin(self, linkedin_url: str) -> Person | None:
        """Return a person by unique LinkedIn URL, or None."""
        result = await self.db.execute(select(Person).where(Person.linkedin_url == linkedin_url))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Person | None:
        """Return a person by email (stored lowercase), or None."""
        result = await self.db.execute(select(Person).where(Person.email == email))
        return result.scalar_one_or_none()

    async def list(
        self,
        limit: int = 20,
        offset: int = 0,
        company_id: UUID | None = None,
    ) -> tuple[list[Person], int]:
        """Return a page of persons, optionally filtered by company."""
        filters = []
        if company_id is not None:
            filters.append(Person.company_id == company_id)

        total_result = await self.db.execute(
            select(func.count()).select_from(Person).where(*filters)
        )
        total = total_result.scalar_one()

        result = await self.db.execute(
            select(Person)
            .where(*filters)
            .order_by(Person.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def update(self, person_id: UUID, data: PersonUpdate) -> Person | None:
        """Apply a partial update. Returns None if the person does not exist."""
        person = await self.get_by_id(person_id)
        if person is None:
            return None

        updates = data.model_dump(exclude_unset=True)
        await self._assert_unique(
            linkedin_url=updates.get("linkedin_url"),
            email=updates.get("email"),
            exclude_id=person_id,
        )
        if "company_id" in updates and updates["company_id"] is not None:
            await self._require_company(updates["company_id"])

        for field, value in updates.items():
            setattr(person, field, value)

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise DuplicateError("Person with this linkedin_url already exists") from None
        await self.db.refresh(person)
        return person

    async def delete(self, person_id: UUID) -> bool:
        """Delete by id. Related drafts are removed (ON DELETE CASCADE)."""
        person = await self.get_by_id(person_id)
        if person is None:
            return False
        await self.db.delete(person)
        await self.db.commit()
        return True

    async def set_company(self, person_id: UUID, company_id: UUID) -> Person | None:
        """Bind a person to a company. Returns None if the person does not exist."""
        person = await self.get_by_id(person_id)
        if person is None:
            return None
        await self._require_company(company_id)
        person.company_id = company_id
        await self.db.commit()
        await self.db.refresh(person)
        return person

    async def get_with_company(self, person_id: UUID) -> Person | None:
        """Load a person and their company in one extra SELECT (selectinload)."""
        result = await self.db.execute(
            select(Person)
            .options(selectinload(Person.company))
            .where(Person.id == person_id)
        )
        return result.scalar_one_or_none()

    async def _require_company(self, company_id: UUID) -> None:
        company = await CompanyService(self.db).get_by_id(company_id)
        if company is None:
            raise NotFoundError(f"Company '{company_id}' not found")

    async def _assert_unique(
        self,
        *,
        linkedin_url: str | None = None,
        email: str | None = None,
        exclude_id: UUID | None = None,
    ) -> None:
        if linkedin_url:
            existing = await self.get_by_linkedin(linkedin_url)
            if existing is not None and existing.id != exclude_id:
                raise DuplicateError(f"Person with linkedin_url '{linkedin_url}' already exists")
        if email:
            existing = await self.get_by_email(email)
            if existing is not None and existing.id != exclude_id:
                raise DuplicateError(f"Person with email '{email}' already exists")

    async def research_from_linkedin(
        self,
        linkedin_url: str,
        company_domain: str | None = None,
    ) -> tuple[Person, Company | None, str]:
        """Enrich a person from LinkedIn. Cache hit skips the external adapter."""
        url = normalize_linkedin_url(linkedin_url)
        existing = await self.get_by_linkedin(url)
        if existing is not None:
            company = None
            if existing.company_id is not None:
                company = await CompanyService(self.db).get_by_id(existing.company_id)
            logger.info("linkedin cache hit url=%s person_id=%s", url, existing.id)
            return existing, company, "cache"

        logger.info("linkedin research start url=%s", url)
        profile = await self.linkedin_service.get_profile(url)
        company = await self._resolve_company(profile.current_company, company_domain)

        person = await self.create(
            PersonCreate(
                first_name=profile.first_name,
                last_name=profile.last_name,
                linkedin_url=url,
                title=profile.current_title,
                company_id=company.id if company is not None else None,
                raw_linkedin_data=profile.model_dump(),
            )
        )
        logger.info(
            "linkedin research created person_id=%s company_id=%s source=%s",
            person.id,
            company.id if company else None,
            profile.source,
        )
        return person, company, profile.source

    async def _resolve_company(
        self,
        company_name: str | None,
        company_domain: str | None,
    ) -> Company | None:
        companies = CompanyService(self.db)
        if company_domain:
            found = await companies.get_by_domain(company_domain)
            if found is None:
                raise NotFoundError(f"Company '{company_domain}' not found")
            return found
        if not company_name:
            return None
        found = await companies.get_by_name(company_name)
        if found is not None:
            return found
        domain = _slugify_domain(company_name)
        existing_domain = await companies.get_by_domain(domain)
        if existing_domain is not None:
            return existing_domain
        try:
            return await companies.create(CompanyCreate(domain=domain, name=company_name))
        except IntegrityError:
            return await companies.get_by_domain(domain)


def _slugify_domain(name: str) -> str:
    """Turn 'Acme Corp' into acme-corp.com for auto-created companies."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        slug = "unknown"
    return f"{slug}.com"
