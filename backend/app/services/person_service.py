"""Person business logic (CRUD + company binding)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import EmailStatus
from app.models.person import Person
from app.schemas.person import PersonCreate, PersonUpdate
from app.services.company_service import CompanyService
from app.services.exceptions import DuplicateError, NotFoundError


class PersonService:
    """CRUD operations for `Person` using an injected async session."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

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
