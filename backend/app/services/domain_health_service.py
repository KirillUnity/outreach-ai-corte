"""Domain health business logic (CRUD + upsert)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain_health import DomainHealth
from app.schemas.company import normalize_domain
from app.schemas.domain_health import DomainHealthCreate, DomainHealthUpdate
from app.services.exceptions import DuplicateError

if TYPE_CHECKING:
    from app.services.deliverability.checker import DeliverabilityChecker


class DomainHealthService:
    """CRUD operations for `DomainHealth` using an injected async session."""

    def __init__(self, db: AsyncSession, checker: DeliverabilityChecker | None = None) -> None:
        self.db = db
        self.checker = checker

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

    async def check_and_save(
        self,
        domain: str,
        *,
        result: dict[str, Any] | None = None,
    ) -> DomainHealth:
        """Run live DNS checks (unless `result` is given) and upsert `DomainHealth`."""
        from app.services.deliverability.checker import DeliverabilityChecker

        normalized = normalize_domain(domain)
        checker = self.checker or DeliverabilityChecker()
        payload = result if result is not None else await checker.check_domain(normalized)
        mx_rows = payload.get("mx", {}).get("records") or []
        mx_strings = [
            f"{row.get('priority')} {row.get('exchange')}".strip()
            for row in mx_rows
            if isinstance(row, dict)
        ]
        checked_at = payload.get("checked_at") or datetime.now(timezone.utc)
        snapshot, _created = await self.upsert(
            DomainHealthCreate(
                domain=normalized,
                spf_record=payload.get("spf", {}).get("record"),
                spf_valid=bool(payload.get("spf", {}).get("valid")),
                dkim_record=payload.get("dkim", {}).get("record"),
                dkim_valid=bool(payload.get("dkim", {}).get("valid")),
                dmarc_record=payload.get("dmarc", {}).get("record"),
                dmarc_policy=payload.get("dmarc", {}).get("policy"),
                mx_records=mx_strings or None,
                checked_at=checked_at,
            )
        )
        return snapshot
