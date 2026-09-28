"""Async Neo4j Bolt driver. No-op when `NEO4J_ENABLED=false` so the API still boots."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings, settings as default_settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """One driver per process — sessions are cheap, drivers are not."""

    def __init__(self, settings: Settings | None = None, driver: Any | None = None) -> None:
        self.settings = settings or default_settings
        cfg = self.settings.neo4j
        self.enabled = bool(cfg.enabled)
        self._driver = driver
        if self.enabled and self._driver is None:
            from neo4j import AsyncGraphDatabase

            self._driver = AsyncGraphDatabase.driver(
                cfg.uri,
                auth=(cfg.user, cfg.password),
                max_connection_pool_size=cfg.max_connection_pool_size,
                connection_timeout=cfg.connection_timeout,
            )

    @property
    def driver(self) -> Any:
        return self._driver

    async def verify_connectivity(self) -> bool:
        """Official handshake — better than RETURN 1 (auth + routing, not just TCP)."""
        if not self.enabled or self._driver is None:
            return False
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception:
            logger.exception("neo4j verify_connectivity failed")
            return False

    async def close(self) -> None:
        if self._driver is None:
            return
        await self._driver.close()
        self._driver = None

    async def execute_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if not self.enabled or self._driver is None:
            return []
        async with self._driver.session(database=self.settings.neo4j.database) as session:
            result = await session.run(query, parameters or {})
            return [record.data() async for record in result]

    async def execute_write(self, query: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.enabled or self._driver is None:
            return {"skipped": True}
        async with self._driver.session(database=self.settings.neo4j.database) as session:
            result = await session.run(query, parameters or {})
            records = [record.data() async for record in result]
            summary = await result.consume()
            counters = getattr(summary, "counters", None)
            return {
                "records": records,
                "nodes_created": getattr(counters, "nodes_created", 0) if counters else 0,
                "relationships_created": getattr(counters, "relationships_created", 0) if counters else 0,
            }


_CLIENT: Neo4jClient | None = None


def get_neo4j_client() -> Neo4jClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = Neo4jClient(default_settings)
    return _CLIENT


def reset_neo4j_client() -> None:
    global _CLIENT
    _CLIENT = None
