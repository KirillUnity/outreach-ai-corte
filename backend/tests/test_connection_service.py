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


async def test_find_shortest_path_empty() -> None:
    out = await _svc(_Fake([])).find_shortest_path(uuid4(), uuid4())
    assert out == []


async def test_find_shortest_path_direct() -> None:
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
    assert out[0]["distance"] == 1
    assert len(out[0]["path"]) == 2


async def test_add_connection_bidirectional() -> None:
    client = _Fake()
    await _svc(client).add_connection(uuid4(), uuid4(), context="met at a meetup")
    query = client.writes[0]
    assert query.count("CONNECTED_TO") == 2
    assert "MERGE (a)-[r1:CONNECTED_TO]->(b)" in query
    assert "MERGE (b)-[r2:CONNECTED_TO]->(a)" in query
