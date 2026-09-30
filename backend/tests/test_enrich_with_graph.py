"""enrich_with_graph node with fake graph collaborators."""

from uuid import uuid4

from app.services.agent.nodes import enrich_with_graph


class _Boom:
    async def compute_influence_score(self, person_id):
        raise RuntimeError("bolt down")

    async def find_connection_path_to_company(self, **kwargs):
        raise RuntimeError("bolt down")

    async def find_hidden_connections(self, **kwargs):
        raise RuntimeError("bolt down")

    async def get_top_decision_makers(self, domain, limit=5):
        raise RuntimeError("bolt down")


class _OkConnections:
    async def compute_influence_score(self, person_id):
        return {"influence_score": 7.5, "direct_connections": 4}

    async def find_connection_path_to_company(self, **kwargs):
        return {
            "path": [
                {"id": str(uuid4()), "name": "Ada"},
                {"id": str(kwargs["person_id"]), "name": "John"},
            ],
            "distance": 1,
        }


def _state(**kwargs):
    base = {
        "person_id": uuid4(),
        "company_data": {"domain": "stripe.com", "name": "Stripe"},
    }
    base.update(kwargs)
    return base


async def test_enrich_no_company_returns_empty_context() -> None:
    out = await enrich_with_graph(_state(company_data={}))
    ctx = out["graph_context"]
    assert ctx["warm_intro_available"] is False
    assert ctx["influence_score"] == 0.0
    assert ctx["warm_intro_distance"] == -1


async def test_enrich_with_influence() -> None:
    out = await enrich_with_graph(_state(), connection_service=_OkConnections())
    assert out["graph_context"]["influence_score"] == 7.5
    assert out["graph_context"]["direct_connections"] == 4


async def test_enrich_with_warm_intro() -> None:
    out = await enrich_with_graph(_state(), connection_service=_OkConnections())
    assert out["graph_context"]["warm_intro_available"] is True
    assert out["graph_context"]["warm_intro_distance"] == 1


async def test_enrich_handles_service_exception() -> None:
    boom = _Boom()
    out = await enrich_with_graph(
        _state(),
        graph_service=boom,
        connection_service=boom,
        recommendation_service=boom,
    )
    ctx = out["graph_context"]
    assert ctx["warm_intro_available"] is False
    assert ctx["influence_score"] == 0.0
    assert "errors" not in out
