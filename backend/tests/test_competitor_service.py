"""CompetitorService with a fake Neo4j client."""

from app.services.graph.competitors import CompetitorService
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


def _svc(client: _Fake) -> CompetitorService:
    return CompetitorService(client, GraphService(client))


async def test_add_competitor_bidirectional() -> None:
    client = _Fake()
    await _svc(client).add_competitor("stripe.com", "square.com")
    query = client.writes[0]
    assert query.count("COMPETITOR_OF") == 2
    assert "MERGE (a)-[r1:COMPETITOR_OF]->(b)" in query
    assert "MERGE (b)-[r2:COMPETITOR_OF]->(a)" in query


async def test_get_competitors_returns_list() -> None:
    rows = [{"competitor": {"domain": "square.com"}, "top_people": []}]
    out = await _svc(_Fake(rows)).get_competitors("stripe.com")
    assert out[0]["competitor"]["domain"] == "square.com"


async def test_auto_detect_same_industry() -> None:
    rows = [{"domain": "adyen.com", "name": "Adyen"}]
    out = await _svc(_Fake(rows)).auto_detect_competitors("stripe.com", "payments")
    assert out == ["adyen.com"]
