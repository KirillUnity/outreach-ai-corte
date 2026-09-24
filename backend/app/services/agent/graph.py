"""Assemble the outreach StateGraph."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from app.core.config import Settings
from app.services.agent.edges import route_after_decide, route_after_load, route_after_validate
from app.services.agent.nodes import (
    check_deliverability_node,
    decide,
    generate_email_node,
    load_person_and_company,
    research_company_if_needed,
    retrieve_rag_context,
    save_and_send_node,
    save_draft_node,
    validate_email_node,
)
from app.services.agent.state import OutreachState
from app.services.company_service import CompanyService
from app.services.deliverability_checker import DeliverabilityChecker
from app.services.email_draft_service import EmailDraftService
from app.services.email_generator import EmailGenerator
from app.services.output_validator import OutputValidator
from app.services.person_service import PersonService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)


def _memory_checkpointer() -> Any:
    try:
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()
    except ImportError:  # pragma: no cover
        from langgraph.checkpoint.memory import InMemorySaver

        return InMemorySaver()


def build_outreach_graph(
    person_service: PersonService,
    company_service: CompanyService,
    rag_service: RAGService,
    email_generator: EmailGenerator,
    validator: OutputValidator,
    deliverability_checker: DeliverabilityChecker,
    draft_service: EmailDraftService,
    settings: Settings,
    *,
    checkpointer: Any = None,
) -> Any:
    """Compile the graph. MemorySaver is the default so pytest needs no extra tables."""
    workflow: StateGraph = StateGraph(OutreachState)

    async def load_person(state: OutreachState) -> dict:
        return await load_person_and_company(state, person_service, company_service)

    async def research_company(state: OutreachState) -> dict:
        return await research_company_if_needed(state, company_service)

    async def retrieve_rag(state: OutreachState) -> dict:
        return await retrieve_rag_context(state, rag_service, email_generator)

    async def generate_email(state: OutreachState) -> dict:
        return await generate_email_node(state, email_generator, person_service, company_service)

    async def validate_email(state: OutreachState) -> dict:
        return await validate_email_node(state, validator)

    async def check_deliverability(state: OutreachState) -> dict:
        return await check_deliverability_node(state, deliverability_checker, settings)

    async def decide_node(state: OutreachState) -> dict:
        return decide(state, settings)

    async def save_draft(state: OutreachState) -> dict:
        return await save_draft_node(state, draft_service)

    async def save_and_send(state: OutreachState) -> dict:
        return await save_and_send_node(state, draft_service)

    workflow.add_node("load_person", load_person)
    workflow.add_node("research_company", research_company)
    workflow.add_node("retrieve_rag", retrieve_rag)
    workflow.add_node("generate_email", generate_email)
    workflow.add_node("validate_email", validate_email)
    workflow.add_node("check_deliverability", check_deliverability)
    workflow.add_node("decide", decide_node)
    workflow.add_node("save_draft", save_draft)
    workflow.add_node("save_and_send", save_and_send)

    workflow.set_entry_point("load_person")
    workflow.add_conditional_edges(
        "load_person",
        route_after_load,
        {"research_company": "research_company", "fail": END},
    )
    workflow.add_edge("research_company", "retrieve_rag")
    workflow.add_edge("retrieve_rag", "generate_email")
    workflow.add_edge("generate_email", "validate_email")
    workflow.add_conditional_edges(
        "validate_email",
        route_after_validate,
        {"generate_email": "generate_email", "check_deliverability": "check_deliverability"},
    )
    workflow.add_edge("check_deliverability", "decide")
    workflow.add_conditional_edges(
        "decide",
        route_after_decide,
        {"save_draft": "save_draft", "save_and_send": "save_and_send"},
    )
    workflow.add_edge("save_draft", END)
    workflow.add_edge("save_and_send", END)

    if checkpointer is None and settings.agent.enable_checkpointing:
        checkpointer = _memory_checkpointer()
        logger.info("agent graph using MemorySaver (in-process checkpoints)")

    return workflow.compile(checkpointer=checkpointer)
