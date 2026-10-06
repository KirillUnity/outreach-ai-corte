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
from app.services.agent.alerts import AlertsService
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
from app.services.tracing import TracingService, get_tracing

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
        "graph_context": None,
        "email_found": None,
        "email_address": None,
        "email_confidence": None,
        "email_source": None,
        "email_candidates_count": 0,
        "email_subject": None,
        "email_body": None,
        "deliverability_ok": None,
        "deliverability_details": None,
        "validation_errors": [],
        "guardrail_results": [],
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

    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        tracing: TracingService | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.tracing = tracing if tracing is not None else get_tracing()
        self.alerts = AlertsService()

    def _build_graph(self) -> Any:
        person_service = PersonService(self.db)
        company_service = CompanyService(self.db)
        rag_service = RAGService(self.settings)
        cost_tracker = CostTracker()
        llm_client = LLMClient(self.settings, cost_tracker=cost_tracker, tracing=self.tracing)
        email_generator = EmailGenerator(
            self.settings, llm_client, rag_service, cost_tracker, tracing=self.tracing
        )
        validator = OutputValidator()
        deliverability_checker = DeliverabilityChecker(DomainHealthService(self.db))
        draft_service = EmailDraftService(self.db, email_generator=email_generator)
        connection_service = None
        graph_service = None
        recommendation_service = None
        try:
            from app.services.neo4j_client import get_neo4j_client

            neo4j = get_neo4j_client()
            if neo4j.enabled:
                from app.services.graph.connections import ConnectionService
                from app.services.graph.graph_service import GraphService

                graph_service = GraphService(neo4j)
                connection_service = ConnectionService(graph_service, neo4j)
                from app.services.graph.recommendations import RecommendationService

                recommendation_service = RecommendationService(neo4j, connection_service)
        except Exception:
            logger.exception("neo4j wiring skipped for outreach agent")
        from app.services.email_finder.finder import EmailFinder

        email_finder = EmailFinder(self.db, self.settings)
        return build_outreach_graph(
            person_service,
            company_service,
            rag_service,
            email_generator,
            validator,
            deliverability_checker,
            draft_service,
            self.settings,
            tracing=self.tracing,
            graph_service=graph_service,
            connection_service=connection_service,
            recommendation_service=recommendation_service,
            email_finder=email_finder,
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
        trace_id = self.tracing.start_trace(
            name=f"outreach_agent_{person_id}",
            metadata={"person_id": str(person_id), "goal": goal, "thread_id": thread_id},
        )
        token = self.tracing.bind_trace(trace_id)
        handler = self.tracing.get_callback_handler(
            trace_name=f"outreach_agent_{person_id}",
            metadata={"person_id": str(person_id), "goal": goal},
            session_id=str(person_id),
        )
        config: dict[str, Any] = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": max(8, self.settings.agent.max_iterations),
        }
        if handler is not None:
            config["callbacks"] = [handler]
        started = time.perf_counter()
        try:
            with self.tracing.trace_node("agent_run", {"person_id": str(person_id), "goal": goal}) as span:
                result = await graph.ainvoke(initial, config=config)
                span.set_output(
                    {
                        "decision": result.get("decision"),
                        "decision_reason": result.get("decision_reason"),
                        "draft_id": str(result.get("draft_id") or ""),
                    }
                )
        finally:
            duration = time.perf_counter() - started
            self.tracing.flush()
            self.tracing.unbind_trace(token)
        await self._persist_run(result, duration)
        self.alerts.check_cost_threshold(float(result.get("total_cost_usd") or 0.0))
        error_n = len(result.get("errors") or [])
        self.alerts.check_error_rate(error_n, 1)
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
