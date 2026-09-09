"""Company business logic (CRUD). Session is injected — do not inherit from AsyncSession."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate


class CompanyService:
    """CRUD operations for `Company` using an injected async session."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: CompanyCreate) -> Company:
        """Insert a company. Caller should handle IntegrityError as a duplicate domain."""
        company = Company(**data.model_dump())
        self.db.add(company)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise
        await self.db.refresh(company)
        return company

    async def get_by_domain(self, domain: str) -> Company | None:
        """Return a company by unique domain, or None."""
        result = await self.db.execute(select(Company).where(Company.domain == domain))
        return result.scalar_one_or_none()

    async def get_by_id(self, id: UUID) -> Company | None:
        """Return a company by primary key, or None."""
        result = await self.db.execute(select(Company).where(Company.id == id))
        return result.scalar_one_or_none()

    async def list(self, limit: int = 20, offset: int = 0) -> tuple[list[Company], int]:
        """Return a page of companies and the total row count."""
        total_result = await self.db.execute(select(func.count()).select_from(Company))
        total = total_result.scalar_one()

        result = await self.db.execute(
            select(Company).order_by(Company.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), total

    async def update(self, domain: str, data: CompanyUpdate) -> Company | None:
        """Apply a partial update. Returns None if the company does not exist."""
        company = await self.get_by_domain(domain)
        if company is None:
            return None

        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(company, field, value)

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise
        await self.db.refresh(company)
        return company

    async def delete(self, domain: str) -> bool:
        """Delete by domain. Returns True if a row was removed."""
        company = await self.get_by_domain(domain)
        if company is None:
            return False
        await self.db.delete(company)
        await self.db.commit()
        return True
