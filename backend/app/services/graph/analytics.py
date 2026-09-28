"""Graph-wide counts, rankings, and connected components (no GDS plugin)."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from app.services.graph import queries as cypher
from app.services.neo4j_client import Neo4jClient


class GraphAnalytics:
    """Cheap analytics that stay within 512m heap — no Graph Data Science library."""

    def __init__(self, client: Neo4jClient) -> None:
        self.client = client

    async def get_graph_stats(self) -> dict[str, Any]:
        node_rows = await self.client.execute_query(cypher.QUERY_NODE_COUNTS, {})
        rel_rows = await self.client.execute_query(cypher.QUERY_REL_COUNTS, {})
        nodes = {str(row.get("label") or "Unknown"): int(row.get("count") or 0) for row in node_rows}
        relationships = {str(row.get("type") or "Unknown"): int(row.get("count") or 0) for row in rel_rows}
        return {"nodes": nodes, "relationships": relationships}

    async def get_top_influencers(self, limit: int = 10) -> list[dict[str, Any]]:
        return await self.client.execute_query(cypher.QUERY_ALL_INFLUENCE, {"limit": limit})

    async def get_company_rankings(self, limit: int = 10) -> list[dict[str, Any]]:
        return await self.client.execute_query(cypher.QUERY_COMPANY_RANKINGS, {"limit": limit})

    async def detect_communities(self, min_size: int = 3) -> list[dict[str, Any]]:
        """Undirected CONNECTED_TO components via BFS (GDS WCC is not installed)."""
        edges = await self.client.execute_query(cypher.QUERY_CONNECTION_EDGES, {})
        graph: dict[str, set[str]] = defaultdict(set)
        for row in edges:
            a, b = str(row.get("a") or ""), str(row.get("b") or "")
            if not a or not b or a == b:
                continue
            graph[a].add(b)
            graph[b].add(a)
        seen: set[str] = set()
        communities: list[dict[str, Any]] = []
        for start in graph:
            if start in seen:
                continue
            queue: deque[str] = deque([start])
            seen.add(start)
            members: list[str] = []
            while queue:
                node = queue.popleft()
                members.append(node)
                for nxt in graph[node]:
                    if nxt not in seen:
                        seen.add(nxt)
                        queue.append(nxt)
            if len(members) >= min_size:
                communities.append({"size": len(members), "member_ids": members})
        communities.sort(key=lambda item: item["size"], reverse=True)
        return communities
