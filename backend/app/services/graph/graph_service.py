"""MERGE/DETACH CRUD for Company, Person, EmailThread."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.company import Company
from app.models.email_draft import EmailDraft
from app.models.person import Person
from app.services.graph import queries as cypher
from app.services.neo4j_client import Neo4jClient

UPSERT_COMPANY = """
MERGE (c:Company {id: $id})
SET c.domain = $domain,
    c.name = $name,
    c.industry = $industry,
    c.size = $size,
    c.updated_at = datetime()
RETURN c {.*} AS node
"""

UPSERT_PERSON = """
MERGE (p:Person {id: $id})
SET p.first_name = $first_name,
    p.last_name = $last_name,
    p.linkedin_url = $linkedin_url,
    p.email = $email,
    p.title = $title,
    p.updated_at = datetime()
RETURN p {.*} AS node
"""

LINK_PERSON_COMPANY = """
MATCH (p:Person {id: $person_id}), (c:Company {id: $company_id})
MERGE (p)-[r:WORKS_AT]->(c)
MERGE (c)-[r2:EMPLOYS]->(p)
SET r.since = datetime()
RETURN p.id AS person_id, c.id AS company_id
"""

UPSERT_THREAD = """
MERGE (t:EmailThread {id: $id})
SET t.subject = $subject,
    t.body_preview = $body_preview,
    t.goal = $goal,
    t.is_sent = $is_sent,
    t.created_at = $created_at
WITH t
MATCH (p:Person {id: $person_id})
MERGE (p)-[:PARTICIPATES_IN]->(t)
WITH t
OPTIONAL MATCH (c:Company {id: $company_id})
FOREACH (_ IN CASE WHEN c IS NULL THEN [] ELSE [1] END |
  MERGE (t)-[:SENT_TO]->(c)
)
RETURN t {.*} AS node
"""

DELETE_PERSON = "MATCH (p:Person {id: $id}) DETACH DELETE p"
DELETE_COMPANY = "MATCH (c:Company {id: $id}) DETACH DELETE c"


class GraphService:
    """Write path into Neo4j. Caller owns Postgres transactions."""

    def __init__(self, client: Neo4jClient) -> None:
        self.client = client

    async def upsert_company(self, company: Company) -> dict[str, Any]:
        size = company.size.value if getattr(company, "size", None) is not None else None
        out = await self.client.execute_write(
            UPSERT_COMPANY,
            {
                "id": str(company.id),
                "domain": company.domain,
                "name": company.name,
                "industry": company.industry,
                "size": size,
            },
        )
        records = out.get("records") or []
        return records[0] if records else {"id": str(company.id)}

    async def upsert_person(self, person: Person) -> dict[str, Any]:
        out = await self.client.execute_write(
            UPSERT_PERSON,
            {
                "id": str(person.id),
                "first_name": person.first_name,
                "last_name": person.last_name,
                "linkedin_url": person.linkedin_url,
                "email": person.email,
                "title": person.title,
            },
        )
        records = out.get("records") or []
        return records[0] if records else {"id": str(person.id)}

    async def link_person_to_company(self, person_id: UUID, company_id: UUID) -> None:
        await self.client.execute_write(
            LINK_PERSON_COMPANY,
            {"person_id": str(person_id), "company_id": str(company_id)},
        )

    async def upsert_email_thread(
        self,
        draft: EmailDraft,
        person: Person,
        company: Company | None,
    ) -> dict[str, Any]:
        created = getattr(draft, "created_at", None)
        created_iso = created.isoformat() if created is not None else None
        goal = draft.goal.value if getattr(draft.goal, "value", None) else str(draft.goal)
        out = await self.client.execute_write(
            UPSERT_THREAD,
            {
                "id": str(draft.id),
                "subject": draft.subject,
                "body_preview": (draft.body or "")[:200],
                "goal": goal,
                "is_sent": bool(draft.is_sent),
                "created_at": created_iso,
                "person_id": str(person.id),
                "company_id": str(company.id) if company is not None else None,
            },
        )
        records = out.get("records") or []
        return records[0] if records else {"id": str(draft.id)}

    async def delete_person(self, person_id: UUID) -> None:
        await self.client.execute_write(DELETE_PERSON, {"id": str(person_id)})

    async def delete_company(self, company_id: UUID) -> None:
        await self.client.execute_write(DELETE_COMPANY, {"id": str(company_id)})

    async def get_company_network(self, domain: str, depth: int = 2, limit: int = 100) -> dict[str, Any]:
        """Employees (depth 1) plus CONNECTED_TO neighbors (depth 2). Always LIMIT."""
        rows = await self.client.execute_query(
            cypher.QUERY_COMPANY_NETWORK, {"domain": domain, "limit": limit}
        )
        nodes: dict[str, dict[str, Any]] = {}
        edges: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in rows:
            company = row.get("company")
            person = row.get("person")
            if company and company.get("id"):
                cid = str(company["id"])
                nodes[cid] = {"id": cid, "label": "Company", **company}
            if person and person.get("id") and company and company.get("id"):
                pid = str(person["id"])
                nodes[pid] = {"id": pid, "label": "Person", **person}
                key = (pid, str(company["id"]), "WORKS_AT")
                edges[key] = {"source": key[0], "target": key[1], "type": key[2]}
        if depth >= 2:
            extra = await self.client.execute_query(
                cypher.QUERY_COMPANY_NETWORK_DEPTH2, {"domain": domain, "limit": limit}
            )
            for row in extra:
                person = row.get("person") or {}
                friend = row.get("friend") or {}
                fc = row.get("friend_company") or {}
                if person.get("id"):
                    nodes[str(person["id"])] = {"id": str(person["id"]), "label": "Person", **person}
                if friend.get("id") and person.get("id"):
                    nodes[str(friend["id"])] = {"id": str(friend["id"]), "label": "Person", **friend}
                    key = (str(person["id"]), str(friend["id"]), "CONNECTED_TO")
                    edges[key] = {"source": key[0], "target": key[1], "type": key[2]}
                if fc.get("id") and friend.get("id"):
                    nodes[str(fc["id"])] = {"id": str(fc["id"]), "label": "Company", **fc}
                    key = (str(friend["id"]), str(fc["id"]), "WORKS_AT")
                    edges[key] = {"source": key[0], "target": key[1], "type": key[2]}
        return {"nodes": list(nodes.values()), "edges": list(edges.values())}

    async def get_person_network(self, person_id: UUID, depth: int = 2, limit: int = 100) -> dict[str, Any]:
        _ = depth
        rows = await self.client.execute_query(
            cypher.QUERY_PERSON_NETWORK, {"person_id": str(person_id), "limit": limit}
        )
        nodes: dict[str, dict[str, Any]] = {}
        edges: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in rows:
            person = row.get("person") or {}
            company = row.get("company") or {}
            other = row.get("other") or {}
            thread = row.get("thread") or {}
            if person.get("id"):
                nodes[str(person["id"])] = {"id": str(person["id"]), "label": "Person", **person}
            if company.get("id") and person.get("id"):
                nodes[str(company["id"])] = {"id": str(company["id"]), "label": "Company", **company}
                key = (str(person["id"]), str(company["id"]), "WORKS_AT")
                edges[key] = {"source": key[0], "target": key[1], "type": key[2]}
            if other.get("id") and person.get("id"):
                nodes[str(other["id"])] = {"id": str(other["id"]), "label": "Person", **other}
                key = (str(person["id"]), str(other["id"]), "CONNECTED_TO")
                edges[key] = {"source": key[0], "target": key[1], "type": key[2]}
            if thread.get("id") and person.get("id"):
                nodes[str(thread["id"])] = {"id": str(thread["id"]), "label": "EmailThread", **thread}
                key = (str(person["id"]), str(thread["id"]), "PARTICIPATES_IN")
                edges[key] = {"source": key[0], "target": key[1], "type": key[2]}
        return {"nodes": list(nodes.values()), "edges": list(edges.values())}

    async def get_top_decision_makers(self, domain: str, limit: int = 10) -> list[dict[str, Any]]:
        return await self.client.execute_query(
            cypher.QUERY_DECISION_MAKERS_AT_COMPANY, {"domain": domain, "limit": limit}
        )

    async def get_recommended_targets(self, domain: str, limit: int = 10) -> list[dict[str, Any]]:
        return await self.client.execute_query(
            cypher.QUERY_RECOMMEND_OUTREACH_TARGETS, {"domain": domain, "limit": limit}
        )
