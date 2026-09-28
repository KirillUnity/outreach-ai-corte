"""Warm-intro and next-target ranking on the outreach graph."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.services.graph import queries as cypher
from app.services.graph.connections import ConnectionService
from app.services.graph.graph_service import GraphService
from app.services.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class RecommendationService:
    """Combine shortest path, influence, and 'not yet emailed'."""

    def __init__(self, client: Neo4jClient, connections: ConnectionService | None = None) -> None:
        self.client = client
        self.connections = connections or ConnectionService(GraphService(client), client)

    async def recommend_warm_intro_paths(
        self,
        person_id: UUID,
        target_company_domain: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        uncontacted = await self.client.execute_query(
            cypher.QUERY_UNCONTACTED_AT_COMPANY,
            {"domain": target_company_domain, "limit": 40},
        )
        scored: list[dict[str, Any]] = []
        for row in uncontacted:
            target = row.get("person") or {}
            tid = target.get("id")
            if not tid:
                continue
            try:
                target_uuid = UUID(str(tid))
            except ValueError:
                continue
            path_info = await self.connections.find_shortest_path(person_id, target_uuid)
            if path_info.get("distance", -1) < 0:
                continue
            influence = await self.connections.compute_influence_score(target_uuid)
            mutuals = await self.connections.find_mutual_connections(person_id, target_uuid)
            scored.append(
                {
                    "target_person": target,
                    "path": path_info.get("path") or [],
                    "distance": int(path_info.get("distance") or 0),
                    "mutual_connections": len(mutuals),
                    "influence_score": float(influence.get("influence_score") or 0.0),
                }
            )
        scored.sort(key=lambda item: (item["distance"], -item["influence_score"]))
        return scored[:limit]

    async def recommend_next_target(self, campaign_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
        """No Campaign table yet — rank uncontacted people with a connection signal.

        ``campaign_id`` is reserved for a later Postgres campaign entity.
        """
        logger.info("recommend_next_target campaign_id=%s (uncontacted heuristic)", campaign_id)
        rows = await self.client.execute_query(
            cypher.QUERY_UNCONTACTED_GLOBAL, {"limit": limit}
        )
        out: list[dict[str, Any]] = []
        for row in rows:
            person = row.get("person") or {}
            pid = person.get("id")
            influence = {"influence_score": 0.0}
            if pid:
                try:
                    influence = await self.connections.compute_influence_score(UUID(str(pid)))
                except ValueError:
                    pass
            out.append(
                {
                    "person": person,
                    "connections_count": int(row.get("connections_count") or 0),
                    "influence_score": float(influence.get("influence_score") or 0.0),
                    "warm_intro_available": int(row.get("connections_count") or 0) > 0,
                }
            )
        out.sort(key=lambda item: (-item["influence_score"], -item["connections_count"]))
        return out[:limit]

    async def find_hidden_connections(
        self,
        person_id: UUID,
        company_domain: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Second-degree people at the account you do not already know directly."""
        return await self.client.execute_query(
            cypher.QUERY_HIDDEN_CONNECTIONS,
            {"person_id": str(person_id), "domain": company_domain, "limit": limit},
        )
