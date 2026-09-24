"""Run the outreach graph and persist an AgentRun row."""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.agent_run import AgentRun
from app.services.agent.graph import build_outreach_graph
from app.services.agent.state import OutreachState
from app.services.company_service import CompanyService
from app.services.cost_tracker import CostTracker
from app.services.deliverability_checker import DeliverabilityChecker
from app.services.domain_health_service import DomainHealthService
from app.services.email_draft_service import EmailDraftService
from app.services.email_generator import EmailGenerator
from app.services.llm_client import LLMClient
from app.services.output_validator import OutputValidator
from app.services.person_service import PersonService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)


def _json_safe(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def empty_outreach_state(
    person_id: UUID,
    goal: str,
    sender_info: dict[str, str],
    **kwargs: Any,
) -> OutreachState:
    """Initial state with reducer lists as empty lists (not omitted)."""
    return {
        "person_id": person_id,
        "goal": goal,
        "sender_name": sender_info["name"],
        "sender_title": sender_info["title"],
        "sender_company": sender_info["company"],
        "language": kwargs.get("language", "en"),
        "max_words": int(kwargs.get("max_words", 120)),
        "person_data": None,
        "company_data": None,
        "company_researched": False,
        "rag_context": None,
        "email_subject": None,
        "email_body": None,
        "deliverability_ok": None,
        "deliverability_details": None,
        "validation_errors": [],
        "draft_id": None,
        "decision": None,
        "decision_reason": None,
        "iteration": 0,
        "total_tokens_input": 0,
        "total_tokens_output": 0,
        "total_cost_usd": 0.0,
        "errors": [],
    }


class OutreachAgentService:
    """Build a per-request graph (services share this request's AsyncSession)."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def _build_graph(self) -> Any:
        person_service = PersonService(self.db)
        company_service = CompanyService(self.db)
        rag_service = RAGService(self.settings)
        cost_tracker = CostTracker()
        llm_client = LLMClient(self.settings, cost_tracker=cost_tracker)
        email_generator = EmailGenerator(
            self.settings, llm_client, rag_service, cost_tracker
        )
        validator = OutputValidator()
        deliverability_checker = DeliverabilityChecker(DomainHealthService(self.db))
        draft_service = EmailDraftService(self.db, email_generator=email_generator)
        return build_outreach_graph(
            person_service,
            company_service,
            rag_service,
            email_generator,
            validator,
            deliverability_checker,
            draft_service,
            self.settings,
        )

    async def run(
        self,
        person_id: UUID,
        goal: str,
        sender_info: dict[str, str],
        **kwargs: Any,
    ) -> OutreachState:
        """Invoke the graph once. thread_id is unique so we never resume a stale run."""
        graph = self._build_graph()
        initial = empty_outreach_state(person_id, goal, sender_info, **kwargs)
        thread_id = f"{person_id}:{uuid4()}"
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": max(8, self.settings.agent.max_iterations),
        }
        started = time.perf_counter()
        result = await graph.ainvoke(initial, config=config)
        duration = time.perf_counter() - started
        await self._persist_run(result, duration)
        return result

    async def list_runs(
        self,
        person_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AgentRun], int]:
        """Newest runs first."""
        filters = []
        if person_id is not None:
            filters.append(AgentRun.person_id == person_id)
        total = (
            await self.db.execute(select(func.count()).select_from(AgentRun).where(*filters))
        ).scalar_one()
        rows = await self.db.execute(
            select(AgentRun)
            .where(*filters)
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars().all()), int(total)

    async def _persist_run(self, state: OutreachState, duration: float) -> None:
        if any("not found" in err.lower() for err in (state.get("errors") or [])):
            logger.info("skip agent_runs persist — person missing")
            return
        row = AgentRun(
            person_id=state["person_id"],
            goal=state.get("goal") or "meeting",
            decision=state.get("decision") or "unknown",
            decision_reason=state.get("decision_reason"),
            iterations=int(state.get("iteration") or 0),
            tokens_input=int(state.get("total_tokens_input") or 0),
            tokens_output=int(state.get("total_tokens_output") or 0),
            cost_usd=float(state.get("total_cost_usd") or 0.0),
            duration_seconds=round(duration, 3),
            final_state=_json_safe(dict(state)),
        )
        self.db.add(row)
        await self.db.commit()
        logger.info(
            "agent_run saved person_id=%s decision=%s duration=%.2f",
            state["person_id"],
            row.decision,
            duration,
        )
