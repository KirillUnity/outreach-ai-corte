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
from app.services.rag_service import RAGService


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


def get_email_generator() -> EmailGenerator:
    """Wire RAG + LLM + cost tracker for one request."""
    cfg = get_settings()
    tracker = CostTracker()
    return EmailGenerator(
        settings=cfg,
        llm_client=LLMClient(cfg, cost_tracker=tracker),
        rag_service=RAGService(cfg),
        cost_tracker=tracker,
    )
