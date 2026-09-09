"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from sqlalchemy import text

from app.api.routers import companies, domain_health, email_drafts, health, persons
from app.core.config import settings
from app.core.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan: verify DB on startup, cleanup on shutdown.

    Startup  → ping PostgreSQL (fail fast if unreachable)
    Shutdown → dispose connection pool
    """
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(companies.router, prefix="/api/v1")
app.include_router(persons.router, prefix="/api/v1")
app.include_router(email_drafts.router, prefix="/api/v1")
app.include_router(domain_health.router, prefix="/api/v1")
