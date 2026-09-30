"""Pydantic payloads for the graph HTTP API."""

from uuid import UUID

from pydantic import BaseModel, Field


class GraphNodeResponse(BaseModel):
    id: UUID
    label: str
    name: str
    properties: dict = Field(default_factory=dict)


class GraphEdgeResponse(BaseModel):
    source: UUID
    target: UUID
    type: str
    properties: dict = Field(default_factory=dict)


class GraphResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]


class PathResponse(BaseModel):
    path: list[GraphNodeResponse]
    distance: int


class PathToCompanyResponse(BaseModel):
    path: list[GraphNodeResponse]
    distance: int
    target: GraphNodeResponse | None = None


class MutualConnectionResponse(BaseModel):
    person: GraphNodeResponse
    company: GraphNodeResponse
    connection_path_length: int


class MutualConnectionsResponse(BaseModel):
    persons: list[GraphNodeResponse]


class InfluenceScoreResponse(BaseModel):
    id: str | None = None
    direct_connections: int
    second_degree_connections: int
    influence_score: float


class CompetitorCreate(BaseModel):
    competitor_domain: str


class CompetitorsResponse(BaseModel):
    competitors: list[dict] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    items: list[dict] = Field(default_factory=list)


class WarmIntroCandidate(BaseModel):
    target_person: GraphNodeResponse
    target_company: GraphNodeResponse
    path: list[GraphNodeResponse]
    distance: int
    mutual_connections: int
    influence_score: float
    has_prior_contact: bool = False


class WarmIntroSearchResponse(BaseModel):
    sender_person_id: UUID | None = None
    target_company_domain: str
    candidates: list[WarmIntroCandidate]
    total: int


class GraphStatsResponse(BaseModel):
    nodes: dict[str, int] = Field(default_factory=dict)
    relationships: dict[str, int] = Field(default_factory=dict)


class SyncResponse(BaseModel):
    companies: int
    persons: int
    threads: int
    duration_seconds: float
