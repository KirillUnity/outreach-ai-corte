"""FastAPI dependency injection helpers."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db as _get_db
from app.services.linkedin_service import LinkedInService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session for a single request."""
    async for session in _get_db():
        yield session


def get_linkedin_service() -> LinkedInService:
    """Build a LinkedIn adapter from process settings (mock unless LINKEDIN_MODE=real)."""
    return LinkedInService(settings)
