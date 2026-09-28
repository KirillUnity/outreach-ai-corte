"""Optional fire-and-forget Neo4j upsert after Postgres writes."""

from __future__ import annotations

import logging
from uuid import UUID

from app.core.config import settings
from app.models.company import Company
from app.models.person import Person

logger = logging.getLogger(__name__)


async def sync_company_after_write(company: Company) -> None:
    if not settings.neo4j.enabled or not settings.neo4j.auto_sync_on_write:
        return
    try:
        from app.services.graph.graph_service import GraphService
        from app.services.neo4j_client import get_neo4j_client

        await GraphService(get_neo4j_client()).upsert_company(company)
    except Exception:
        logger.exception("neo4j auto-sync company failed id=%s", company.id)


async def sync_person_after_write(person: Person) -> None:
    if not settings.neo4j.enabled or not settings.neo4j.auto_sync_on_write:
        return
    try:
        from app.services.graph.graph_service import GraphService
        from app.services.neo4j_client import get_neo4j_client

        graph = GraphService(get_neo4j_client())
        await graph.upsert_person(person)
        if person.company_id is not None:
            await graph.link_person_to_company(person.id, person.company_id)
    except Exception:
        logger.exception("neo4j auto-sync person failed id=%s", person.id)


async def delete_company_in_graph(company_id: UUID) -> None:
    if not settings.neo4j.enabled or not settings.neo4j.auto_sync_on_write:
        return
    try:
        from app.services.graph.graph_service import GraphService
        from app.services.neo4j_client import get_neo4j_client

        await GraphService(get_neo4j_client()).delete_company(company_id)
    except Exception:
        logger.exception("neo4j auto-delete company failed id=%s", company_id)


async def delete_person_in_graph(person_id: UUID) -> None:
    if not settings.neo4j.enabled or not settings.neo4j.auto_sync_on_write:
        return
    try:
        from app.services.graph.graph_service import GraphService
        from app.services.neo4j_client import get_neo4j_client

        await GraphService(get_neo4j_client()).delete_person(person_id)
    except Exception:
        logger.exception("neo4j auto-delete person failed id=%s", person_id)
