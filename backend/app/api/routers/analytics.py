"""Cost, quality, guardrail, and decision dashboards (read-only)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/costs/summary")
async def get_costs_summary(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Total LLM-related cost from persisted agent runs."""
    return await AnalyticsService(db).costs_summary(days)


@router.get("/costs/by-model")
async def get_costs_by_model(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Draft counts and estimated cost grouped by `generation_context.model`."""
    return await AnalyticsService(db).costs_by_model(days)


@router.get("/quality/scores")
async def get_quality_scores(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Average heuristic quality scores stored on drafts."""
    return await AnalyticsService(db).quality_scores(days)


@router.get("/guardrails/failures")
async def get_guardrail_failures(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """How often each rail returned passed=false."""
    return await AnalyticsService(db).guardrail_failures(days)


@router.get("/agent/decisions")
async def get_agent_decisions(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """send / hold / reject mix from `agent_runs`."""
    return await AnalyticsService(db).agent_decisions(days)
