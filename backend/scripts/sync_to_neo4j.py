"""CLI: python -m scripts.sync_to_neo4j  (cwd / PYTHONPATH = backend)."""

from __future__ import annotations

import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.services.graph.connections import ConnectionService
from app.services.graph.graph_service import GraphService
from app.services.graph.sync_service import GraphSyncService
from app.services.neo4j_client import get_neo4j_client

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    client = get_neo4j_client()
    if not client.enabled:
        print("NEO4J_ENABLED=false — nothing to sync")
        return
    ok = await client.verify_connectivity()
    if not ok:
        raise SystemExit("Neo4j is not reachable")
    graph = GraphService(client)
    connections = ConnectionService(graph, client)
    async with AsyncSessionLocal() as db:
        result = await GraphSyncService(graph, connections, db).sync_all()
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
