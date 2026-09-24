"""LangGraph outreach agent HTTP API."""

import logging
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_settings
from app.core.config import Settings
from app.models.agent_run import AgentRun
from app.schemas.agent import AgentRunListResponse, AgentRunRequest, AgentRunResponse
from app.services.agent.agent_service import OutreachAgentService
from app.services.agent.state import OutreachState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


def _from_state(state: OutreachState) -> AgentRunResponse:
    return AgentRunResponse(
        draft_id=state.get("draft_id"),
        decision=state.get("decision") or "unknown",
        decision_reason=state.get("decision_reason"),
        email_subject=state.get("email_subject"),
        email_body=state.get("email_body"),
        validation_errors=list(state.get("validation_errors") or []),
        deliverability_ok=state.get("deliverability_ok"),
        tokens_input=int(state.get("total_tokens_input") or 0),
        tokens_output=int(state.get("total_tokens_output") or 0),
        estimated_cost_usd=float(state.get("total_cost_usd") or 0.0),
        iterations=int(state.get("iteration") or 0),
        errors=list(state.get("errors") or []),
    )


def _from_row(row: AgentRun) -> AgentRunResponse:
    final = row.final_state or {}
    return AgentRunResponse(
        draft_id=final.get("draft_id"),
        decision=row.decision,
        decision_reason=row.decision_reason,
        email_subject=final.get("email_subject"),
        email_body=final.get("email_body"),
        validation_errors=list(final.get("validation_errors") or []),
        deliverability_ok=final.get("deliverability_ok"),
        tokens_input=row.tokens_input,
        tokens_output=row.tokens_output,
        estimated_cost_usd=row.cost_usd,
        iterations=row.iterations,
        errors=list(final.get("errors") or []),
        created_at=row.created_at,
    )


@router.post(
    "/outreach",
    response_model=AgentRunResponse,
    summary="Run the outreach LangGraph agent",
)
async def run_outreach_agent(
    data: AgentRunRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AgentRunResponse:
    """Research (if needed) → RAG → generate → validate → deliverability → decide → save."""
    service = OutreachAgentService(db, settings)
    start = time.perf_counter()
    try:
        state = await service.run(
            person_id=data.person_id,
            goal=data.goal.value,
            sender_info={
                "name": data.sender_name,
                "title": data.sender_title,
                "company": data.sender_company,
            },
            language=data.language,
            max_words=data.max_words,
        )
    except Exception as exc:
        logger.exception("Agent run failed for person %s", data.person_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Agent failed: {exc}",
        ) from None

    duration = time.perf_counter() - start
    logger.info(
        "Agent finished in %.2fs decision=%s person_id=%s",
        duration,
        state.get("decision"),
        data.person_id,
    )
    return _from_state(state)


@router.get(
    "/runs",
    response_model=AgentRunListResponse,
    summary="List past agent runs",
)
async def list_agent_runs(
    person_id: UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AgentRunListResponse:
    """Newest first. `final_state` lives on the row for debugging."""
    items, total = await OutreachAgentService(db, settings).list_runs(
        person_id=person_id, limit=limit, offset=offset
    )
    return AgentRunListResponse(
        items=[_from_row(row) for row in items],
        total=total,
        limit=limit,
        offset=offset,
    )
