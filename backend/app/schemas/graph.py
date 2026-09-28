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


class MutualConnectionResponse(BaseModel):
    person: GraphNodeResponse
    company: GraphNodeResponse
    connection_path_length: int


class SyncResponse(BaseModel):
    companies: int
    persons: int
    threads: int
    duration_seconds: float
