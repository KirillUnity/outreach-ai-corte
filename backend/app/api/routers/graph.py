"""Read APIs over Neo4j plus admin Postgres→graph sync."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_neo4j_client, get_settings
from app.core.config import Settings
from app.schemas.graph import (
    CompetitorCreate,
    CompetitorsResponse,
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphResponse,
    GraphStatsResponse,
    InfluenceScoreResponse,
    MutualConnectionResponse,
    MutualConnectionsResponse,
    PathResponse,
    PathToCompanyResponse,
    RecommendationResponse,
    SyncResponse,
)
from app.services.company_service import CompanyService
from app.services.graph.analytics import GraphAnalytics
from app.services.graph.competitors import CompetitorService
from app.services.graph.connections import ConnectionService
from app.services.graph.graph_service import GraphService
from app.services.graph.recommendations import RecommendationService
from app.services.graph.sync_service import GraphSyncService
from app.services.neo4j_client import Neo4jClient

router = APIRouter(prefix="/graph", tags=["graph"])


def _as_uuid(value: object) -> UUID | None:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _node(payload: dict | None, label: str) -> GraphNodeResponse | None:
    if not payload or not payload.get("id"):
        return None
    nid = _as_uuid(payload["id"])
    if nid is None:
        return None
    if label == "Company":
        name = str(payload.get("name") or payload.get("domain") or nid)
    else:
        name = f"{payload.get('first_name') or ''} {payload.get('last_name') or ''}".strip() or str(
            payload.get("name") or nid
        )
    return GraphNodeResponse(id=nid, label=label, name=name, properties=dict(payload))


def _path_nodes(hops: list[dict]) -> list[GraphNodeResponse]:
    path_nodes: list[GraphNodeResponse] = []
    for hop in hops:
        nid = _as_uuid(hop.get("id"))
        if nid is None:
            continue
        path_nodes.append(
            GraphNodeResponse(
                id=nid,
                label="Person",
                name=str(hop.get("name") or nid),
                properties=dict(hop),
            )
        )
    return path_nodes


def _graph_payload(raw: dict) -> GraphResponse:
    nodes: dict[UUID, GraphNodeResponse] = {}
    edges: list[GraphEdgeResponse] = []
    for item in raw.get("nodes") or []:
        label = str(item.get("label") or "Person")
        node = _node(item, label)
        if node:
            nodes[node.id] = node
    seen: set[tuple[UUID, UUID, str]] = set()
    for item in raw.get("edges") or []:
        source = _as_uuid(item.get("source"))
        target = _as_uuid(item.get("target"))
        rel = str(item.get("type") or "")
        if source is None or target is None:
            continue
        key = (source, target, rel)
        if key in seen:
            continue
        seen.add(key)
        edges.append(GraphEdgeResponse(source=source, target=target, type=rel, properties={}))
    return GraphResponse(nodes=list(nodes.values()), edges=edges)


def _connections(client: Neo4jClient) -> ConnectionService:
    return ConnectionService(GraphService(client), client)


@router.get("/company/{domain}/network", response_model=GraphResponse)
async def company_network(
    domain: str,
    depth: int = Query(default=2, ge=1, le=3),
    client: Neo4jClient = Depends(get_neo4j_client),
) -> GraphResponse:
    """Company plus employees (depth 2 also pulls CONNECTED_TO neighbors)."""
    _require_graph(client)
    raw = await GraphService(client).get_company_network(domain, depth=depth, limit=100)
    return _graph_payload(raw)


@router.get("/person/{person_id}/network", response_model=GraphResponse)
async def person_network(
    person_id: UUID,
    depth: int = Query(default=2, ge=1, le=3),
    client: Neo4jClient = Depends(get_neo4j_client),
) -> GraphResponse:
    _require_graph(client)
    raw = await GraphService(client).get_person_network(person_id, depth=depth, limit=100)
    return _graph_payload(raw)


@router.get("/path", response_model=PathResponse)
async def shortest_path(
    from_person_id: UUID,
    to_person_id: UUID,
    max_depth: int = Query(default=6, ge=1, le=6),
    client: Neo4jClient = Depends(get_neo4j_client),
) -> PathResponse:
    _require_graph(client)
    result = await _connections(client).find_shortest_path(
        from_person_id, to_person_id, max_depth=max_depth
    )
    hops = result.get("path") or []
    if not hops or int(result.get("distance", -1)) < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no path")
    return PathResponse(path=_path_nodes(hops), distance=int(result.get("distance") or 0))


@router.get("/person/{person_id}/path-to-company", response_model=PathToCompanyResponse)
async def path_to_company(
    person_id: UUID,
    company_domain: str,
    max_depth: int = Query(default=6, ge=1, le=6),
    client: Neo4jClient = Depends(get_neo4j_client),
) -> PathToCompanyResponse:
    _require_graph(client)
    result = await _connections(client).find_connection_path_to_company(
        person_id, company_domain, max_depth=max_depth
    )
    hops = result.get("path") or []
    if not hops or int(result.get("distance", -1)) < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no path")
    return PathToCompanyResponse(
        path=_path_nodes(hops),
        distance=int(result.get("distance") or 0),
        target=_node(result.get("target"), "Person"),
    )


@router.get("/persons/mutual", response_model=MutualConnectionsResponse)
async def mutual_between_persons(
    person_a_id: UUID,
    person_b_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    client: Neo4jClient = Depends(get_neo4j_client),
) -> MutualConnectionsResponse:
    _require_graph(client)
    rows = await _connections(client).find_mutual_connections(person_a_id, person_b_id, limit=limit)
    persons: list[GraphNodeResponse] = []
    for row in rows:
        node = _node(row if isinstance(row, dict) else None, "Person")
        if node:
            persons.append(node)
    return MutualConnectionsResponse(persons=persons)


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
    rows = await _connections(client).find_friends_at_company(person_id, company.id)
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


@router.get("/person/{person_id}/influence", response_model=InfluenceScoreResponse)
async def person_influence(
    person_id: UUID,
    client: Neo4jClient = Depends(get_neo4j_client),
) -> InfluenceScoreResponse:
    _require_graph(client)
    data = await _connections(client).compute_influence_score(person_id)
    return InfluenceScoreResponse(**data)


@router.get("/company/{domain}/competitors", response_model=CompetitorsResponse)
async def list_competitors(
    domain: str,
    limit: int = Query(default=20, ge=1, le=100),
    client: Neo4jClient = Depends(get_neo4j_client),
) -> CompetitorsResponse:
    _require_graph(client)
    graph = GraphService(client)
    rows = await CompetitorService(client, graph).get_competitors(domain, limit=limit)
    return CompetitorsResponse(competitors=rows)


@router.post("/company/{domain}/competitors", response_model=CompetitorsResponse)
async def add_competitor(
    domain: str,
    body: CompetitorCreate,
    client: Neo4jClient = Depends(get_neo4j_client),
) -> CompetitorsResponse:
    _require_graph(client)
    svc = CompetitorService(client, GraphService(client))
    await svc.add_competitor(domain, body.competitor_domain)
    rows = await svc.get_competitors(domain, limit=20)
    return CompetitorsResponse(competitors=rows)


@router.get("/company/{domain}/decision-makers")
async def decision_makers(
    domain: str,
    limit: int = Query(default=10, ge=1, le=50),
    client: Neo4jClient = Depends(get_neo4j_client),
) -> list[dict]:
    _require_graph(client)
    return await GraphService(client).get_top_decision_makers(domain, limit=limit)


@router.get("/company/{domain}/recommended-targets")
async def recommended_targets(
    domain: str,
    limit: int = Query(default=10, ge=1, le=50),
    client: Neo4jClient = Depends(get_neo4j_client),
) -> list[dict]:
    _require_graph(client)
    return await GraphService(client).get_recommended_targets(domain, limit=limit)


@router.get("/person/{person_id}/warm-intro-paths", response_model=RecommendationResponse)
async def warm_intro_paths(
    person_id: UUID,
    target_company_domain: str,
    limit: int = Query(default=5, ge=1, le=20),
    client: Neo4jClient = Depends(get_neo4j_client),
) -> RecommendationResponse:
    _require_graph(client)
    items = await RecommendationService(client, _connections(client)).recommend_warm_intro_paths(
        person_id, target_company_domain, limit=limit
    )
    return RecommendationResponse(items=items)


@router.get("/analytics/stats", response_model=GraphStatsResponse)
async def graph_stats(client: Neo4jClient = Depends(get_neo4j_client)) -> GraphStatsResponse:
    _require_graph(client)
    data = await GraphAnalytics(client).get_graph_stats()
    return GraphStatsResponse(**data)


@router.get("/analytics/top-influencers")
async def top_influencers(
    limit: int = Query(default=10, ge=1, le=50),
    client: Neo4jClient = Depends(get_neo4j_client),
) -> list[dict]:
    _require_graph(client)
    return await GraphAnalytics(client).get_top_influencers(limit=limit)


@router.get("/analytics/company-rankings")
async def company_rankings(
    limit: int = Query(default=10, ge=1, le=50),
    client: Neo4jClient = Depends(get_neo4j_client),
) -> list[dict]:
    _require_graph(client)
    return await GraphAnalytics(client).get_company_rankings(limit=limit)


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
