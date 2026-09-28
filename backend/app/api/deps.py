"""FastAPI dependency injection helpers."""

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.database import get_db as _get_db
from app.services.cost_tracker import CostTracker
from app.services.email_generator import EmailGenerator
from app.services.linkedin_service import LinkedInService
from app.services.llm_client import LLMClient
from app.services.neo4j_client import Neo4jClient, get_neo4j_client as _get_neo4j_client
from app.services.rag_service import RAGService
from app.services.tracing import get_tracing


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session for a single request."""
    async for session in _get_db():
        yield session


@lru_cache
def get_settings() -> Settings:
    """Process-wide Settings. Parsing .env on every request is wasted work."""
    return Settings()


def get_linkedin_service() -> LinkedInService:
    """Build a LinkedIn adapter from process settings (mock unless LINKEDIN_MODE=real)."""
    return LinkedInService(settings)


@lru_cache
def get_neo4j_client() -> Neo4jClient:
    """Process-wide Bolt driver. A new driver per request would leak sockets and RAM."""
    return _get_neo4j_client()


def get_email_generator() -> EmailGenerator:
    """Wire RAG + LLM + cost tracker for one request."""
    cfg = get_settings()
    tracker = CostTracker()
    tracing = get_tracing()
    return EmailGenerator(
        settings=cfg,
        llm_client=LLMClient(cfg, cost_tracker=tracker, tracing=tracing),
        rag_service=RAGService(cfg),
        cost_tracker=tracker,
        tracing=tracing,
    )
