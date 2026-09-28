"""Competitor_of relationships and industry-based detection."""

from __future__ import annotations

from typing import Any

from app.services.graph import queries as cypher
from app.services.graph.graph_service import GraphService
from app.services.neo4j_client import Neo4jClient


class CompetitorService:
    """Bidirectional COMPETITOR_OF edges plus landscape views."""

    def __init__(self, client: Neo4jClient, graph_service: GraphService) -> None:
        self.client = client
        self.graph_service = graph_service

    async def add_competitor(self, company_domain: str, competitor_domain: str) -> None:
        await self.client.execute_write(
            cypher.QUERY_ADD_COMPETITOR,
            {"a": company_domain, "b": competitor_domain},
        )

    async def get_competitors(self, domain: str, limit: int = 20) -> list[dict[str, Any]]:
        return await self.client.execute_query(
            cypher.QUERY_COMPANY_COMPETITORS, {"domain": domain, "limit": limit}
        )

    async def auto_detect_competitors(self, domain: str, industry: str) -> list[str]:
        rows = await self.client.execute_query(
            cypher.QUERY_AUTO_DETECT_COMPETITORS,
            {"domain": domain, "industry": industry},
        )
        return [str(row.get("domain")) for row in rows if row.get("domain")]

    async def get_competitive_landscape(self, domain: str) -> dict[str, Any]:
        """Company, competitors, sample people, no full-scan neighbor explosion."""
        competitors = await self.get_competitors(domain, limit=20)
        people_by_domain: dict[str, list[dict[str, Any]]] = {}
        for row in competitors:
            comp = row.get("competitor") or {}
            key = str(comp.get("domain") or "")
            people_by_domain[key] = list(row.get("top_people") or [])
        return {
            "domain": domain,
            "competitors": competitors,
            "people_by_competitor": people_by_domain,
        }
