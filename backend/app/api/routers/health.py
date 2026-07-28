"""Health check endpoint — verifies PostgreSQL and ChromaDB connectivity."""

import httpx
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

router = APIRouter()


class ServiceCheck(BaseModel):
    """Status of a single dependency."""

    status: str = Field(..., examples=["up", "down"])
    detail: str | None = None


class HealthResponse(BaseModel):
    """Aggregated health check response."""

    status: str = Field(..., examples=["healthy", "degraded"])
    postgres: ServiceCheck
    chromadb: ServiceCheck


async def _check_postgres(db: AsyncSession) -> ServiceCheck:
    """Execute a lightweight query against PostgreSQL."""
    try:
        await db.execute(text("SELECT 1"))
        return ServiceCheck(status="up")
    except Exception as exc:
        return ServiceCheck(status="down", detail=str(exc))


async def _check_chromadb() -> ServiceCheck:
    """Ping ChromaDB heartbeat endpoint."""
    url = f"{settings.chroma_base_url}/api/v1/heartbeat"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            response.raise_for_status()
        return ServiceCheck(status="up")
    except Exception as exc:
        return ServiceCheck(status="down", detail=str(exc))


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns status of PostgreSQL and ChromaDB dependencies.",
)
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> HealthResponse | JSONResponse:
    """Check all external dependencies and return aggregated status."""
    postgres = await _check_postgres(db)
    chromadb = await _check_chromadb()

    all_up = postgres.status == "up" and chromadb.status == "up"
    body = HealthResponse(
        status="healthy" if all_up else "degraded",
        postgres=postgres,
        chromadb=chromadb,
    )

    if not all_up:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=body.model_dump(),
        )
    return body
