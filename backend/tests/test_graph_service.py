"""GraphService Cypher shape — fake client, no Bolt."""

from types import SimpleNamespace
from uuid import uuid4

from app.services.graph.graph_service import GraphService


class _CapturingClient:
    def __init__(self) -> None:
        self.writes: list[tuple[str, dict]] = []

    async def execute_write(self, query: str, parameters: dict | None = None) -> dict:
        self.writes.append((query, parameters or {}))
        return {"records": [{"node": {"id": parameters.get("id") if parameters else None}}]}


def _company() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        domain="acme.com",
        name="Acme",
        industry="SaaS",
        size=SimpleNamespace(value="small"),
    )


async def test_upsert_company_query_correct() -> None:
    client = _CapturingClient()
    await GraphService(client).upsert_company(_company())
    query, params = client.writes[0]
    assert "MERGE" in query
    assert "(c:Company {id: $id})" in query
    assert params["domain"] == "acme.com"


async def test_link_person_to_company_creates_bidirectional() -> None:
    client = _CapturingClient()
    pid, cid = uuid4(), uuid4()
    await GraphService(client).link_person_to_company(pid, cid)
    query, params = client.writes[0]
    assert "MERGE (p)-[r:WORKS_AT]->(c)" in query
    assert "MERGE (c)-[r2:EMPLOYS]->(p)" in query
    assert params["person_id"] == str(pid)
    assert params["company_id"] == str(cid)


async def test_delete_person_uses_detach_delete() -> None:
    client = _CapturingClient()
    pid = uuid4()
    await GraphService(client).delete_person(pid)
    query, params = client.writes[0]
    assert "DETACH DELETE" in query
    assert params["id"] == str(pid)
