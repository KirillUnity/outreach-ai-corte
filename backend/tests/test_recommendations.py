"""RecommendationService with a dispatching fake client."""

from uuid import uuid4

from app.services.graph.connections import ConnectionService
from app.services.graph.graph_service import GraphService
from app.services.graph.recommendations import RecommendationService


class _Empty:
    async def execute_query(self, query: str, parameters: dict | None = None) -> list:
        _ = query, parameters
        return []

    async def execute_write(self, query: str, parameters: dict | None = None) -> dict:
        _ = query, parameters
        return {"records": []}


class _WithData:
    def __init__(self, me, target) -> None:
        self.me = me
        self.target = target

    async def execute_query(self, query: str, parameters: dict | None = None) -> list:
        _ = parameters
        if "shortestPath((sender)-[:CONNECTED_TO*1..6]-(target))" in query:
            return [
                {
                    "target": {
                        "id": str(self.target),
                        "first_name": "Pat",
                        "last_name": "",
                    },
                    "company": {"id": str(uuid4()), "domain": "square.com", "name": "Square"},
                    "path_nodes": [
                        {"id": str(self.me), "name": "Me"},
                        {"id": str(self.target), "name": "Pat"},
                    ],
                    "distance": 1,
                    "mutual_connections": 1,
                    "influence_score": 4.0,
                }
            ]
        return []

    async def execute_write(self, query: str, parameters: dict | None = None) -> dict:
        _ = query, parameters
        return {"records": []}


def _svc(client) -> RecommendationService:
    return RecommendationService(client, ConnectionService(GraphService(client), client))


async def test_recommend_warm_intro_paths_empty() -> None:
    out = await _svc(_Empty()).recommend_warm_intro_paths(uuid4(), "square.com")
    assert out == []


async def test_recommend_warm_intro_paths_with_data() -> None:
    me, target = uuid4(), uuid4()
    out = await _svc(_WithData(me, target)).recommend_warm_intro_paths(me, "square.com")
    assert len(out) == 1
    assert out[0]["distance"] == 1
    assert out[0]["influence_score"] == 4.0
    assert out[0]["mutual_connections"] == 1
