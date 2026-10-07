"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routers import (
    agent,
    analytics,
    articles,
    companies,
    crm,
    domain_health,
    email_drafts,
    email_finder,
    enrichment,
    graph,
    health,
    persons,
    sequences,
    warmup,
)
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.api.deps import get_neo4j_client
from app.services.tracing import get_tracing
from app.services.warmup.scheduler import WarmupScheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan: verify DB on startup, cleanup on shutdown.

    Startup  → ping PostgreSQL (fail fast if unreachable)
    Shutdown → dispose connection pool
    """
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    if settings.neo4j.enabled:
        try:
            from app.services.graph.init_schema import GraphSchemaInitializer

            client = get_neo4j_client()
            await GraphSchemaInitializer(client).init_constraints_and_indexes()
        except Exception:
            import logging

            logging.getLogger(__name__).exception("neo4j schema init skipped")
    scheduler = WarmupScheduler(settings)
    await scheduler.start(AsyncSessionLocal)
    try:
        yield
    finally:
        await scheduler.stop()
        get_tracing().flush()
    if settings.neo4j.enabled:
        client = get_neo4j_client()
        await client.close()
        from app.services.neo4j_client import reset_neo4j_client

        reset_neo4j_client()
        get_neo4j_client.cache_clear()
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(articles.router, prefix="/api/v1")
app.include_router(companies.router, prefix="/api/v1")
app.include_router(persons.router, prefix="/api/v1")
app.include_router(email_drafts.router, prefix="/api/v1")
app.include_router(email_finder.router, prefix="/api/v1")
app.include_router(enrichment.router, prefix="/api/v1")
app.include_router(sequences.router, prefix="/api/v1")
app.include_router(crm.router, prefix="/api/v1")
app.include_router(domain_health.router, prefix="/api/v1")
app.include_router(agent.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")
app.include_router(warmup.router, prefix="/api/v1")
