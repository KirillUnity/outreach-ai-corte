"""GraphAnalytics with a fake Neo4j client."""

from app.services.graph.analytics import GraphAnalytics


class _Fake:
    def __init__(self, by_key: dict[str, list] | None = None) -> None:
        self.by_key = by_key or {}

    async def execute_query(self, query: str, parameters: dict | None = None) -> list:
        _ = parameters
        if "labels(n)[0]" in query:
            return self.by_key.get("nodes", [])
        if "type(r)" in query:
            return self.by_key.get("rels", [])
        if "influence_score" in query:
            return self.by_key.get("influence", [])
        if "employees" in query:
            return self.by_key.get("rankings", [])
        if "CONNECTED_TO" in query:
            return self.by_key.get("edges", [])
        return []


async def test_get_graph_stats_empty() -> None:
    out = await GraphAnalytics(_Fake()).get_graph_stats()
    assert out == {"nodes": {}, "relationships": {}}


async def test_get_top_influencers_sorted() -> None:
    rows = [
        {"id": "a", "influence_score": 9.0},
        {"id": "b", "influence_score": 3.0},
    ]
    out = await GraphAnalytics(_Fake({"influence": rows})).get_top_influencers()
    assert out[0]["influence_score"] >= out[1]["influence_score"]


async def test_company_rankings_ordered() -> None:
    rows = [
        {"domain": "a.com", "employees": 10, "competitors": 1},
        {"domain": "b.com", "employees": 2, "competitors": 0},
    ]
    out = await GraphAnalytics(_Fake({"rankings": rows})).get_company_rankings()
    assert out[0]["employees"] >= out[1]["employees"]
