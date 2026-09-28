"""Person-to-person paths and intro-to-account lookups."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.services.graph.graph_service import GraphService
from app.services.neo4j_client import Neo4jClient

ADD_CONNECTION = """
MATCH (a:Person {id: $a_id}), (b:Person {id: $b_id})
MERGE (a)-[r1:CONNECTED_TO]->(b)
MERGE (b)-[r2:CONNECTED_TO]->(a)
SET r1.context = $context, r2.context = $context, r1.created_at = datetime()
RETURN a.id AS a, b.id AS b
"""

# Variable-length *..$n is not always valid; cap hops at 6 in the pattern.
SHORTEST_PATH_FIXED = """
MATCH (a:Person {id: $from_id}), (b:Person {id: $to_id})
MATCH path = shortestPath((a)-[:CONNECTED_TO*1..6]-(b))
RETURN [node IN nodes(path) | {
  id: node.id,
  name: coalesce(node.first_name, '') + ' ' + coalesce(node.last_name, '')
}] AS path, length(path) AS distance
"""

MUTUAL = """
MATCH (me:Person {id: $person_id})-[:CONNECTED_TO]-(friend:Person)-[:WORKS_AT]->(c:Company {id: $company_id})
RETURN friend {.*} AS person, c {.*} AS company, 1 AS connection_path_length
"""


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
            ADD_CONNECTION,
            {"a_id": str(person_a_id), "b_id": str(person_b_id), "context": context},
        )

    async def find_shortest_path(
        self,
        from_id: UUID,
        to_id: UUID,
        max_depth: int = 6,
    ) -> list[dict[str, Any]]:
        _ = max_depth  # 1..6 hop cap is in the Cypher pattern (*1..6)
        rows = await self.client.execute_query(
            SHORTEST_PATH_FIXED,
            {"from_id": str(from_id), "to_id": str(to_id)},
        )
        if not rows:
            return []
        return rows

    async def find_mutual_connections(
        self,
        person_id: UUID,
        target_company_id: UUID,
    ) -> list[dict[str, Any]]:
        return await self.client.execute_query(
            MUTUAL,
            {"person_id": str(person_id), "company_id": str(target_company_id)},
        )
