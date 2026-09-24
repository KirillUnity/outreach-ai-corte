"""Company business logic (CRUD). Session is injected — do not inherit from AsyncSession."""

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.exceptions import NotFoundError
from app.services.rag_service import RAGService
from app.services.site_parser import ParseResult, SiteParser

logger = logging.getLogger(__name__)


class CompanyService:
    """CRUD operations for `Company` using an injected async session."""

    def __init__(
        self,
        db: AsyncSession,
        parser: SiteParser | None = None,
        rag: RAGService | None = None,
    ) -> None:
        self.db = db
        self._parser = parser
        self._rag = rag

    @property
    def parser(self) -> SiteParser:
        """Lazy default parser so tests can inject a fake without touching the network."""
        if self._parser is None:
            self._parser = SiteParser(settings)
        return self._parser

    @property
    def rag(self) -> RAGService:
        """Lazy RAG so tests can inject a fake embedder / Chroma client."""
        if self._rag is None:
            self._rag = RAGService(settings)
        return self._rag

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

    async def get_by_name(self, name: str) -> Company | None:
        """Case-insensitive match on company name. First hit wins."""
        result = await self.db.execute(
            select(Company).where(func.lower(Company.name) == name.strip().lower()).limit(1)
        )
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

    async def research(self, domain: str) -> tuple[Company, ParseResult, int]:
        """Parse the site, persist raw_site_text, then index chunks in Chroma."""
        company = await self.get_by_domain(domain)
        if company is None:
            raise NotFoundError(f"Company '{domain}' not found")

        parsed = await self.parser.parse_company_site(domain)
        if parsed.raw_text:
            company.raw_site_text = parsed.raw_text
        if not company.description and parsed.description:
            company.description = parsed.description
        if not company.name and parsed.title:
            company.name = parsed.title[:255]

        await self.db.commit()
        await self.db.refresh(company)

        chunks_indexed = 0
        if company.raw_site_text:
            try:
                chunks_indexed = await self.rag.index_company(
                    company_id=company.id,
                    domain=company.domain,
                    text=company.raw_site_text,
                )
            except Exception as exc:
                logger.exception("RAG index failed domain=%s", domain)
                parsed.errors.append(f"RAG index failed: {exc}")

        logger.info(
            "research done domain=%s pages=%s errors=%s chars=%s chunks=%s",
            domain,
            parsed.pages_parsed,
            len(parsed.errors),
            len(parsed.raw_text),
            chunks_indexed,
        )
        return company, parsed, chunks_indexed
