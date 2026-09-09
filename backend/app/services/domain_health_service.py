"""Domain health business logic (CRUD + upsert)."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain_health import DomainHealth
from app.schemas.domain_health import DomainHealthCreate, DomainHealthUpdate
from app.services.exceptions import DuplicateError


class DomainHealthService:
    """CRUD operations for `DomainHealth` using an injected async session."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: DomainHealthCreate) -> DomainHealth:
        """Insert a snapshot. Caller should handle DuplicateError on unique domain."""
        row = DomainHealth(**data.model_dump())
        self.db.add(row)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise DuplicateError(f"Domain health for '{data.domain}' already exists") from None
        await self.db.refresh(row)
        return row

    async def get_by_domain(self, domain: str) -> DomainHealth | None:
        """Return a snapshot by unique domain, or None."""
        result = await self.db.execute(select(DomainHealth).where(DomainHealth.domain == domain))
        return result.scalar_one_or_none()

    async def list(self, limit: int = 20, offset: int = 0) -> tuple[list[DomainHealth], int]:
        """Return a page of snapshots and the total row count."""
        total_result = await self.db.execute(select(func.count()).select_from(DomainHealth))
        total = total_result.scalar_one()

        result = await self.db.execute(
            select(DomainHealth)
            .order_by(DomainHealth.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def update(self, domain: str, data: DomainHealthUpdate) -> DomainHealth | None:
        """Apply a partial update. Returns None if the domain does not exist."""
        row = await self.get_by_domain(domain)
        if row is None:
            return None

        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(row, field, value)

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise DuplicateError("Domain health domain already exists") from None
        await self.db.refresh(row)
        return row

    async def delete(self, domain: str) -> bool:
        """Delete by domain. Returns True if a row was removed."""
        row = await self.get_by_domain(domain)
        if row is None:
            return False
        await self.db.delete(row)
        await self.db.commit()
        return True

    async def upsert(self, data: DomainHealthCreate) -> tuple[DomainHealth, bool]:
        """Create or replace by domain. Returns (row, created)."""
        existing = await self.get_by_domain(data.domain)
        if existing is None:
            try:
                return await self.create(data), True
            except DuplicateError:
                existing = await self.get_by_domain(data.domain)
                if existing is None:
                    raise

        for field, value in data.model_dump().items():
            setattr(existing, field, value)
        await self.db.commit()
        await self.db.refresh(existing)
        return existing, False
