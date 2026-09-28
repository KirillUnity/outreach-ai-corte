"""Read APIs over Neo4j plus admin Postgres→graph sync."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_neo4j_client, get_settings
from app.core.config import Settings
from app.schemas.graph import (
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphResponse,
    MutualConnectionResponse,
    PathResponse,
    SyncResponse,
)
from app.services.company_service import CompanyService
from app.services.graph.connections import ConnectionService
from app.services.graph.graph_service import GraphService
from app.services.graph.sync_service import GraphSyncService
from app.services.neo4j_client import Neo4jClient

router = APIRouter(prefix="/graph", tags=["graph"])

COMPANY_NETWORK = """
MATCH (c:Company {domain: $domain})
OPTIONAL MATCH (c)<-[r:WORKS_AT]-(p:Person)
RETURN c {.*} AS company, p {.*} AS person
LIMIT $limit
"""

PERSON_NETWORK = """
MATCH (p:Person {id: $person_id})
OPTIONAL MATCH (p)-[r:WORKS_AT]->(c:Company)
OPTIONAL MATCH (p)-[:CONNECTED_TO]-(other:Person)
RETURN p {.*} AS person, c {.*} AS company, other {.*} AS other
LIMIT $limit
"""

DEPTH2_EXTRA = """
MATCH (c:Company {domain: $domain})<-[:WORKS_AT]-(p:Person)-[:CONNECTED_TO]-(friend:Person)
RETURN p {.*} AS person, friend {.*} AS friend
LIMIT $limit
"""


def _node(payload: dict | None, label: str) -> GraphNodeResponse | None:
    if not payload or not payload.get("id"):
        return None
    nid = UUID(str(payload["id"]))
    if label == "Company":
        name = str(payload.get("name") or payload.get("domain") or nid)
    else:
        name = f"{payload.get('first_name') or ''} {payload.get('last_name') or ''}".strip() or str(
            nid
        )
    return GraphNodeResponse(id=nid, label=label, name=name, properties=dict(payload))


@router.get("/company/{domain}/network", response_model=GraphResponse)
async def company_network(
    domain: str,
    depth: int = Query(default=2, ge=1, le=3),
    client: Neo4jClient = Depends(get_neo4j_client),
) -> GraphResponse:
    """Company plus employees (depth 2 also pulls CONNECTED_TO neighbors)."""
    _require_graph(client)
    limit = 100
    rows = await client.execute_query(COMPANY_NETWORK, {"domain": domain, "limit": limit})
    nodes: dict[UUID, GraphNodeResponse] = {}
    edges: list[GraphEdgeResponse] = []
    for row in rows:
        company = _node(row.get("company"), "Company")
        person = _node(row.get("person"), "Person")
        if company:
            nodes[company.id] = company
        if person and company:
            nodes[person.id] = person
            edges.append(
                GraphEdgeResponse(source=person.id, target=company.id, type="WORKS_AT", properties={})
            )
    if depth >= 2:
        extra = await client.execute_query(DEPTH2_EXTRA, {"domain": domain, "limit": limit})
        for row in extra:
            person = _node(row.get("person"), "Person")
            friend = _node(row.get("friend"), "Person")
            if person:
                nodes[person.id] = person
            if friend and person:
                nodes[friend.id] = friend
                edges.append(
                    GraphEdgeResponse(
                        source=person.id, target=friend.id, type="CONNECTED_TO", properties={}
                    )
                )
    return GraphResponse(nodes=list(nodes.values()), edges=edges)


@router.get("/person/{person_id}/network", response_model=GraphResponse)
async def person_network(
    person_id: UUID,
    depth: int = Query(default=2, ge=1, le=3),
    client: Neo4jClient = Depends(get_neo4j_client),
) -> GraphResponse:
    _require_graph(client)
    _ = depth
    rows = await client.execute_query(
        PERSON_NETWORK, {"person_id": str(person_id), "limit": 100}
    )
    nodes: dict[UUID, GraphNodeResponse] = {}
    edges: list[GraphEdgeResponse] = []
    for row in rows:
        person = _node(row.get("person"), "Person")
        company = _node(row.get("company"), "Company")
        other = _node(row.get("other"), "Person")
        if person:
            nodes[person.id] = person
        if company and person:
            nodes[company.id] = company
            edges.append(
                GraphEdgeResponse(source=person.id, target=company.id, type="WORKS_AT", properties={})
            )
        if other and person:
            nodes[other.id] = other
            edges.append(
                GraphEdgeResponse(
                    source=person.id, target=other.id, type="CONNECTED_TO", properties={}
                )
            )
    return GraphResponse(nodes=list(nodes.values()), edges=edges)


@router.get("/path", response_model=PathResponse)
async def shortest_path(
    from_person_id: UUID,
    to_person_id: UUID,
    max_depth: int = Query(default=6, ge=1, le=6),
    client: Neo4jClient = Depends(get_neo4j_client),
) -> PathResponse:
    _require_graph(client)
    svc = ConnectionService(GraphService(client), client)
    rows = await svc.find_shortest_path(from_person_id, to_person_id, max_depth=max_depth)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no path")
    row = rows[0]
    hops = row.get("path") or []
    path_nodes = []
    for hop in hops:
        nid = UUID(str(hop["id"]))
        path_nodes.append(
            GraphNodeResponse(
                id=nid,
                label="Person",
                name=str(hop.get("name") or nid),
                properties=dict(hop),
            )
        )
    return PathResponse(path=path_nodes, distance=int(row.get("distance") or 0))


@router.get("/person/{person_id}/mutual-connections", response_model=list[MutualConnectionResponse])
async def mutual_connections(
    person_id: UUID,
    target_company_domain: str,
    db: AsyncSession = Depends(get_db),
    client: Neo4jClient = Depends(get_neo4j_client),
) -> list[MutualConnectionResponse]:
    _require_graph(client)
    company = await CompanyService(db).get_by_domain(target_company_domain)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company not found")
    svc = ConnectionService(GraphService(client), client)
    rows = await svc.find_mutual_connections(person_id, company.id)
    out: list[MutualConnectionResponse] = []
    for row in rows:
        person = _node(row.get("person"), "Person")
        co = _node(row.get("company"), "Company")
        if person and co:
            out.append(
                MutualConnectionResponse(
                    person=person,
                    company=co,
                    connection_path_length=int(row.get("connection_path_length") or 1),
                )
            )
    return out


@router.post("/sync", response_model=SyncResponse)
async def sync_from_postgres(
    db: AsyncSession = Depends(get_db),
    client: Neo4jClient = Depends(get_neo4j_client),
    cfg: Settings = Depends(get_settings),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> SyncResponse:
    """Full rebuild of the graph from Postgres. Requires GRAPH_SYNC_TOKEN unless DEBUG."""
    _require_graph(client)
    token = cfg.graph_sync_token
    allowed = (token and x_admin_token == token) or (cfg.debug and not token)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin token required")
    graph = GraphService(client)
    connections = ConnectionService(graph, client)
    result = await GraphSyncService(graph, connections, db).sync_all()
    return SyncResponse(**result)


def _require_graph(client: Neo4jClient) -> None:
    if not client.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j is disabled",
        )
