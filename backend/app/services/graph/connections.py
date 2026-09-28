"""Person-to-person paths, mutuals, influence, and intro-to-account lookups."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.services.graph import queries as cypher
from app.services.graph.graph_service import GraphService
from app.services.neo4j_client import Neo4jClient


class ConnectionService:
    """Intro graph on top of GraphService."""

    def __init__(self, graph_service: GraphService, client: Neo4jClient) -> None:
        self.graph_service = graph_service
        self.client = client

    async def add_connection(
        self,
        person_a_id: UUID,
        person_b_id: UUID,
        context: str | None = None,
    ) -> None:
        await self.client.execute_write(
            cypher.QUERY_ADD_CONNECTION,
            {"a_id": str(person_a_id), "b_id": str(person_b_id), "context": context},
        )

    async def find_shortest_path(
        self,
        from_person_id: UUID,
        to_person_id: UUID,
        max_depth: int = 6,
    ) -> dict[str, Any]:
        """Cypher hop cap is *1..6 (params cannot expand variable length)."""
        _ = max_depth
        rows = await self.client.execute_query(
            cypher.QUERY_SHORTEST_PATH,
            {"from_id": str(from_person_id), "to_id": str(to_person_id)},
        )
        if not rows or not rows[0].get("path"):
            return {"path": [], "distance": -1}
        row = rows[0]
        return {"path": list(row.get("path") or []), "distance": int(row.get("distance") or 0)}

    async def find_mutual_connections(
        self,
        person_a_id: UUID,
        person_b_id: UUID,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        rows = await self.client.execute_query(
            cypher.QUERY_MUTUAL_CONNECTIONS,
            {
                "person_a_id": str(person_a_id),
                "person_b_id": str(person_b_id),
                "limit": limit,
            },
        )
        return [row.get("mutual") or row for row in rows]

    async def find_friends_at_company(
        self,
        person_id: UUID,
        target_company_id: UUID,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """People you know who already work at the target account."""
        return await self.client.execute_query(
            cypher.QUERY_FRIENDS_AT_COMPANY,
            {
                "person_id": str(person_id),
                "company_id": str(target_company_id),
                "limit": limit,
            },
        )

    async def find_connection_path_to_company(
        self,
        person_id: UUID,
        target_company_domain: str,
        max_depth: int = 6,
    ) -> dict[str, Any]:
        _ = max_depth
        rows = await self.client.execute_query(
            cypher.QUERY_PATH_TO_COMPANY,
            {"person_id": str(person_id), "domain": target_company_domain},
        )
        if not rows or not rows[0].get("path"):
            return {"path": [], "distance": -1, "target": None}
        row = rows[0]
        return {
            "path": list(row.get("path") or []),
            "distance": int(row.get("distance") or 0),
            "target": row.get("target"),
        }

    async def compute_influence_score(self, person_id: UUID) -> dict[str, Any]:
        rows = await self.client.execute_query(
            cypher.QUERY_INFLUENCE_SCORE, {"person_id": str(person_id)}
        )
        if not rows:
            return {
                "id": str(person_id),
                "direct_connections": 0,
                "second_degree_connections": 0,
                "influence_score": 0.0,
            }
        row = rows[0]
        return {
            "id": str(row.get("id") or person_id),
            "direct_connections": int(row.get("direct_connections") or 0),
            "second_degree_connections": int(row.get("second_degree_connections") or 0),
            "influence_score": float(row.get("influence_score") or 0.0),
        }
