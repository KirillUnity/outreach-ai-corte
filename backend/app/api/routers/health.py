"""Health check endpoint — verifies PostgreSQL, ChromaDB, and LLM config."""

import asyncio

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_settings
from app.core.config import Settings
from app.core.database import get_db
from app.services.chroma_client import get_chroma_client, reset_chroma_client

router = APIRouter()


class ServiceCheck(BaseModel):
    """Status of a single dependency."""

    status: str = Field(..., examples=["up", "down", "misconfigured"])
    detail: str | None = None


class HealthResponse(BaseModel):
    """Aggregated health check response."""

    status: str = Field(..., examples=["healthy", "degraded"])
    postgres: ServiceCheck
    chromadb: ServiceCheck
    llm: ServiceCheck


async def _check_postgres(db: AsyncSession) -> ServiceCheck:
    """Execute a lightweight query against PostgreSQL."""
    try:
        await db.execute(text("SELECT 1"))
        return ServiceCheck(status="up")
    except Exception as exc:
        return ServiceCheck(status="down", detail=str(exc))


def _chroma_heartbeat() -> None:
    get_chroma_client().heartbeat()


async def _check_chromadb() -> ServiceCheck:
    """Ping ChromaDB through the shared HttpClient (not a raw HTTP guess)."""
    try:
        await asyncio.to_thread(_chroma_heartbeat)
        return ServiceCheck(status="up")
    except Exception as exc:
        reset_chroma_client()
        return ServiceCheck(status="down", detail=str(exc))


def _check_llm(cfg: Settings) -> ServiceCheck:
    """Inspect LLM config only — never spend tokens on a health probe."""
    llm = cfg.llm
    if llm.mode == "mock":
        return ServiceCheck(status="up", detail="mock mode")
    if llm.provider == "openai" and not llm.openai_api_key:
        return ServiceCheck(status="misconfigured", detail="OPENAI_API_KEY is empty")
    if llm.provider == "openrouter" and not llm.openrouter_api_key:
        return ServiceCheck(status="misconfigured", detail="OPENROUTER_API_KEY is empty")
    return ServiceCheck(status="up", detail=f"provider={llm.provider} model={llm.default_model}")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns status of PostgreSQL, ChromaDB, and LLM configuration.",
)
async def health_check(
    db: AsyncSession = Depends(get_db),
    cfg: Settings = Depends(get_settings),
) -> HealthResponse | JSONResponse:
    """Check required infra. LLM misconfig degrades status but does not 503."""
    postgres = await _check_postgres(db)
    chromadb = await _check_chromadb()
    llm = _check_llm(cfg)

    infra_up = postgres.status == "up" and chromadb.status == "up"
    llm_ok = llm.status == "up"
    body = HealthResponse(
        status="healthy" if infra_up and llm_ok else "degraded",
        postgres=postgres,
        chromadb=chromadb,
        llm=llm,
    )

    if not infra_up:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=body.model_dump(),
        )
    return body
