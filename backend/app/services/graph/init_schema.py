"""Constraints and indexes — run once at API startup, IF NOT EXISTS."""

from __future__ import annotations

import logging

from app.services.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

_CONSTRAINTS = (
    "CREATE CONSTRAINT company_id_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT company_domain_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.domain IS UNIQUE",
    "CREATE CONSTRAINT person_id_unique IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT person_linkedin_unique IF NOT EXISTS FOR (p:Person) REQUIRE p.linkedin_url IS UNIQUE",
)

_INDEXES = (
    "CREATE INDEX company_name_idx IF NOT EXISTS FOR (c:Company) ON (c.name)",
    "CREATE INDEX person_email_idx IF NOT EXISTS FOR (p:Person) ON (p.email)",
)


class GraphSchemaInitializer:
    """Idempotent Cypher DDL."""

    def __init__(self, client: Neo4jClient) -> None:
        self.client = client

    async def init_constraints_and_indexes(self) -> None:
        if not self.client.enabled:
            logger.info("neo4j schema skip — disabled")
            return
        for statement in (*_CONSTRAINTS, *_INDEXES):
            await self.client.execute_write(statement)
        logger.info("neo4j constraints and indexes ready")

    async def is_initialized(self) -> bool:
        if not self.client.enabled:
            return False
        rows = await self.client.execute_query("SHOW CONSTRAINTS YIELD name RETURN name")
        names = {str(row.get("name") or "") for row in rows}
        return "company_id_unique" in names
