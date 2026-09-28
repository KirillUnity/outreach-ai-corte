"""Postgres → Neo4j batch and per-entity sync (eventual consistency)."""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import Company
from app.models.email_draft import EmailDraft
from app.models.person import Person
from app.services.graph.connections import ConnectionService
from app.services.graph.graph_service import GraphService

logger = logging.getLogger(__name__)


class GraphSyncService:
    """Source of truth stays Postgres; Neo4j is a query index."""

    def __init__(
        self,
        graph_service: GraphService,
        connection_service: ConnectionService,
        db: AsyncSession,
    ) -> None:
        self.graph_service = graph_service
        self.connection_service = connection_service
        self.db = db

    async def sync_all(self) -> dict[str, Any]:
        started = time.perf_counter()
        companies = list((await self.db.execute(select(Company))).scalars().all())
        for company in companies:
            await self.graph_service.upsert_company(company)
        persons = list((await self.db.execute(select(Person))).scalars().all())
        for person in persons:
            await self.graph_service.upsert_person(person)
            if person.company_id is not None:
                await self.graph_service.link_person_to_company(person.id, person.company_id)
        drafts = list(
            (
                await self.db.execute(select(EmailDraft).options(selectinload(EmailDraft.person)))
            ).scalars().all()
        )
        threads = 0
        company_by_id = {c.id: c for c in companies}
        for draft in drafts:
            person = draft.person
            if person is None:
                continue
            company = company_by_id.get(person.company_id) if person.company_id else None
            await self.graph_service.upsert_email_thread(draft, person, company)
            threads += 1
        duration = time.perf_counter() - started
        result = {
            "companies": len(companies),
            "persons": len(persons),
            "threads": threads,
            "duration_seconds": round(duration, 3),
        }
        logger.info("graph sync_all %s", result)
        return result

    async def sync_company(self, company_id: UUID) -> dict[str, Any]:
        company = (
            await self.db.execute(select(Company).where(Company.id == company_id))
        ).scalar_one_or_none()
        if company is None:
            return {"ok": False, "reason": "company not found"}
        await self.graph_service.upsert_company(company)
        return {"ok": True, "id": str(company.id)}

    async def sync_person(self, person_id: UUID) -> dict[str, Any]:
        person = (
            await self.db.execute(select(Person).where(Person.id == person_id))
        ).scalar_one_or_none()
        if person is None:
            return {"ok": False, "reason": "person not found"}
        await self.graph_service.upsert_person(person)
        if person.company_id is not None:
            await self.graph_service.link_person_to_company(person.id, person.company_id)
        return {"ok": True, "id": str(person.id)}
