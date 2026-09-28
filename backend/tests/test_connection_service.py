"""ConnectionService with a fake Neo4j client."""

from uuid import uuid4

from app.services.graph.connections import ConnectionService
from app.services.graph.graph_service import GraphService


class _Fake:
    def __init__(self, rows: list | None = None) -> None:
        self.rows = list(rows or [])
        self.writes: list[str] = []

    async def execute_query(self, query: str, parameters: dict | None = None) -> list:
        _ = query, parameters
        return list(self.rows)

    async def execute_write(self, query: str, parameters: dict | None = None) -> dict:
        self.writes.append(query)
        return {"records": []}


def _svc(client: _Fake) -> ConnectionService:
    return ConnectionService(GraphService(client), client)


async def test_find_shortest_path_no_path_returns_empty() -> None:
    out = await _svc(_Fake([])).find_shortest_path(uuid4(), uuid4())
    assert out == {"path": [], "distance": -1}


async def test_find_shortest_path_returns_path() -> None:
    a, b = uuid4(), uuid4()
    rows = [
        {
            "path": [
                {"id": str(a), "name": "Ada Lovelace"},
                {"id": str(b), "name": "Alan Turing"},
            ],
            "distance": 1,
        }
    ]
    out = await _svc(_Fake(rows)).find_shortest_path(a, b)
    assert out["distance"] == 1
    assert len(out["path"]) == 2


async def test_mutual_connections_finds_common() -> None:
    mutual_id = uuid4()
    rows = [{"mutual": {"id": str(mutual_id), "first_name": "Grace"}}]
    out = await _svc(_Fake(rows)).find_mutual_connections(uuid4(), uuid4())
    assert out[0]["id"] == str(mutual_id)


async def test_influence_score_calculation() -> None:
    pid = uuid4()
    rows = [
        {
            "id": str(pid),
            "direct_connections": 2,
            "second_degree_connections": 4,
            "influence_score": 4.0,
        }
    ]
    out = await _svc(_Fake(rows)).compute_influence_score(pid)
    assert out["influence_score"] == 4.0
    assert out["direct_connections"] == 2


async def test_add_connection_bidirectional() -> None:
    client = _Fake()
    await _svc(client).add_connection(uuid4(), uuid4(), context="met at a meetup")
    query = client.writes[0]
    assert query.count("CONNECTED_TO") == 2
    assert "MERGE (a)-[r1:CONNECTED_TO]->(b)" in query
    assert "MERGE (b)-[r2:CONNECTED_TO]->(a)" in query
