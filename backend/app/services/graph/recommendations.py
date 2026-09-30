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


def _person_node(payload: dict[str, Any] | None, fallback_name: str = "") -> dict[str, Any] | None:
    if not payload or not payload.get("id"):
        return None
    first = str(payload.get("first_name") or "")
    last = str(payload.get("last_name") or "")
    name = f"{first} {last}".strip() or str(payload.get("name") or fallback_name or payload["id"])
    return {
        "id": str(payload["id"]),
        "label": "Person",
        "name": name,
        "properties": dict(payload),
    }


def _company_node(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload or not payload.get("id"):
        return None
    return {
        "id": str(payload["id"]),
        "label": "Company",
        "name": str(payload.get("name") or payload.get("domain") or payload["id"]),
        "properties": dict(payload),
    }


def _path_nodes(hops: list[Any] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for hop in hops or []:
        if not isinstance(hop, dict) or not hop.get("id"):
            continue
        out.append(
            {
                "id": str(hop["id"]),
                "label": "Person",
                "name": str(hop.get("name") or hop["id"]).strip(),
                "properties": dict(hop),
            }
        )
    return out


class RecommendationService:
    """Combine shortest path, influence, and 'not yet emailed'."""

    def __init__(self, client: Neo4jClient, connections: ConnectionService | None = None) -> None:
        self.client = client
        self.connections = connections or ConnectionService(GraphService(client), client)

    async def recommend_warm_intro_paths(
        self,
        person_id: UUID,
        target_company_domain: str,
        limit: int = 10,
        max_depth: int = 6,
    ) -> list[dict[str, Any]]:
        """Uncontacted people at the account, ranked by short path then influence."""
        rows = await self.client.execute_query(
            cypher.QUERY_WARM_INTRO_CANDIDATES,
            {
                "sender_id": str(person_id),
                "target_domain": target_company_domain,
                "limit": limit,
            },
        )
        scored: list[dict[str, Any]] = []
        for row in rows:
            target = _person_node(row.get("target"))
            company = _company_node(row.get("company"))
            if target is None or company is None:
                continue
            distance = int(row.get("distance") if row.get("distance") is not None else -1)
            if distance > max_depth:
                continue
            scored.append(
                {
                    "target_person": target,
                    "target_company": company,
                    "path": _path_nodes(row.get("path_nodes")),
                    "distance": distance,
                    "mutual_connections": int(row.get("mutual_connections") or 0),
                    "influence_score": float(row.get("influence_score") or 0.0),
                    "has_prior_contact": False,
                }
            )
        scored.sort(
            key=lambda item: (
                999 if int(item["distance"]) < 0 else int(item["distance"]),
                -float(item["influence_score"]),
            )
        )
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
