"""RecommendationService ranking with a fake Neo4j client."""

from uuid import uuid4

from app.services.graph.connections import ConnectionService
from app.services.graph.graph_service import GraphService
from app.services.graph.recommendations import RecommendationService


class _Fake:
    def __init__(self, rows: list | None = None) -> None:
        self.rows = list(rows or [])

    async def execute_query(self, query: str, parameters: dict | None = None) -> list:
        _ = query, parameters
        return list(self.rows)

    async def execute_write(self, query: str, parameters: dict | None = None) -> dict:
        _ = query, parameters
        return {"records": []}


def _svc(client: _Fake) -> RecommendationService:
    return RecommendationService(client, ConnectionService(GraphService(client), client))


def _candidate(*, distance: int, influence: float, tid: str | None = None) -> dict:
    person_id = tid or str(uuid4())
    company_id = str(uuid4())
    return {
        "target": {
            "id": person_id,
            "first_name": "Pat",
            "last_name": "Lee",
            "title": "VP Sales",
        },
        "company": {"id": company_id, "domain": "square.com", "name": "Square"},
        "path_nodes": [
            {"id": str(uuid4()), "name": "Me"},
            {"id": person_id, "name": "Pat Lee"},
        ],
        "distance": distance,
        "mutual_connections": 1,
        "influence_score": influence,
    }


async def test_recommend_warm_intro_paths_returns_sorted() -> None:
    far = _candidate(distance=3, influence=90.0)
    near = _candidate(distance=1, influence=1.0)
    out = await _svc(_Fake([far, near])).recommend_warm_intro_paths(uuid4(), "square.com")
    assert [row["distance"] for row in out] == [1, 3]


async def test_recommend_warm_intro_paths_excludes_contacted() -> None:
    """Contacted people never appear because the Cypher uses NOT PARTICIPATES_IN."""
    from app.services.graph import queries as cypher

    assert "NOT (target)-[:PARTICIPATES_IN]->(:EmailThread)" in cypher.QUERY_WARM_INTRO_CANDIDATES
    out = await _svc(_Fake([])).recommend_warm_intro_paths(uuid4(), "square.com")
    assert out == []


async def test_recommend_returns_influence_score() -> None:
    row = _candidate(distance=1, influence=4.0)
    out = await _svc(_Fake([row])).recommend_warm_intro_paths(uuid4(), "square.com")
    assert out[0]["influence_score"] == 4.0
    assert "target_person" in out[0]
    assert out[0]["has_prior_contact"] is False
