"""LangGraph nodes. Each returns a partial state update and logs its name."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.core.config import Settings
from app.models.enums import EmailGoal
from app.schemas.email_draft import EmailDraftCreate, EmailGenerationRequest
from app.services.agent.state import OutreachState
from app.services.company_service import CompanyService
from app.services.deliverability_checker import DeliverabilityChecker, infer_sender_domain
from app.services.email_draft_service import EmailDraftService
from app.services.email_generator import EmailGenerator
from app.services.output_validator import OutputValidator
from app.services.person_service import PersonService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)


def _person_dump(person: Any) -> dict[str, Any]:
    return {
        "id": str(person.id),
        "first_name": person.first_name,
        "last_name": person.last_name,
        "title": person.title,
        "company_id": str(person.company_id) if person.company_id else None,
        "email": person.email,
    }


def _company_dump(company: Any | None) -> dict[str, Any] | None:
    if company is None:
        return None
    return {
        "id": str(company.id),
        "domain": company.domain,
        "name": company.name,
        "raw_site_text": company.raw_site_text,
    }


async def load_person_and_company(
    state: OutreachState,
    person_service: PersonService,
    company_service: CompanyService,
) -> dict[str, Any]:
    """Load Person + optional Company. Missing person is a hard stop."""
    logger.info("node=load_person person_id=%s", state["person_id"])
    person = await person_service.get_by_id(state["person_id"])
    if person is None:
        return {"errors": [f"Person {state['person_id']} not found"]}

    company = None
    if person.company_id is not None:
        company = await company_service.get_by_id(person.company_id)

    researched = bool(company is not None and company.raw_site_text)
    return {
        "person_data": _person_dump(person),
        "company_data": _company_dump(company),
        "company_researched": researched,
    }


async def research_company_if_needed(
    state: OutreachState,
    company_service: CompanyService,
) -> dict[str, Any]:
    """Parse + index the site when we have a company but no raw_site_text."""
    company = state.get("company_data") or {}
    domain = company.get("domain")
    already = bool(state.get("company_researched"))
    logger.info("node=research_company domain=%s already=%s", domain, already)
    if already or not domain:
        return {"company_researched": already}

    try:
        researched, parsed, _chunks = await company_service.research(domain)
        return {
            "company_researched": True,
            "company_data": _company_dump(researched),
            "errors": list(parsed.errors) if parsed.errors else [],
        }
    except Exception as exc:
        logger.exception("node=research_company failed domain=%s", domain)
        return {"company_researched": False, "errors": [f"research failed: {exc}"]}


async def retrieve_rag_context(
    state: OutreachState,
    rag_service: RAGService,
    email_generator: EmailGenerator,
) -> dict[str, Any]:
    """Semantic search over the company collection."""
    company = state.get("company_data") or {}
    domain = company.get("domain")
    logger.info("node=retrieve_rag domain=%s", domain)
    if not domain:
        return {"rag_context": []}

    person_data = state.get("person_data") or {}
    person = type("P", (), person_data)()
    request = EmailGenerationRequest(
        person_id=state["person_id"],
        goal=_goal(state["goal"]),
        sender_name=state["sender_name"],
        sender_title=state["sender_title"],
        sender_company=state["sender_company"],
        language="ru" if state.get("language") == "ru" else "en",
        max_words=state.get("max_words") or 120,
    )
    company_obj = type("C", (), company)()
    query = email_generator._build_search_query(person, request, company_obj)
    try:
        hits = await rag_service.search(domain, query, top_k=5)
    except Exception as exc:
        logger.exception("node=retrieve_rag failed domain=%s", domain)
        return {"rag_context": [], "errors": [f"rag failed: {exc}"]}
    return {"rag_context": [str(hit.get("text") or "") for hit in hits if hit.get("text")]}


async def generate_email_node(
    state: OutreachState,
    email_generator: EmailGenerator,
    person_service: PersonService,
    company_service: CompanyService,
) -> dict[str, Any]:
    """Call EmailGenerator and bump iteration so the validate loop can stop."""
    iteration = int(state.get("iteration") or 0) + 1
    logger.info("node=generate_email iteration=%s", iteration)
    person = await person_service.get_by_id(state["person_id"])
    if person is None:
        return {"errors": [f"Person {state['person_id']} not found"], "iteration": iteration}

    company = None
    if person.company_id is not None:
        company = await company_service.get_by_id(person.company_id)

    request = EmailGenerationRequest(
        person_id=state["person_id"],
        goal=_goal(state["goal"]),
        sender_name=state["sender_name"],
        sender_title=state["sender_title"],
        sender_company=state["sender_company"],
        language="ru" if state.get("language") == "ru" else "en",
        max_words=state.get("max_words") or 120,
    )
    try:
        result = await email_generator.generate(person, company, request)
    except Exception as exc:
        logger.exception("node=generate_email failed")
        return {"errors": [f"generate failed: {exc}"], "iteration": iteration}

    return {
        "email_subject": result.get("subject"),
        "email_body": result.get("body"),
        "iteration": iteration,
        "total_tokens_input": int(state.get("total_tokens_input") or 0)
        + int(result.get("tokens_input") or 0),
        "total_tokens_output": int(state.get("total_tokens_output") or 0)
        + int(result.get("tokens_output") or 0),
        "total_cost_usd": float(state.get("total_cost_usd") or 0.0)
        + float(result.get("estimated_cost_usd") or 0.0),
        "rag_context": result.get("rag_context_used") or state.get("rag_context") or [],
    }


async def validate_email_node(state: OutreachState, validator: OutputValidator) -> dict[str, Any]:
    """Run OutputValidator. Reducer appends; we send the new errors only."""
    subject = state.get("email_subject") or ""
    body = state.get("email_body") or ""
    max_words = int(state.get("max_words") or 120)
    _ok, errors = validator.validate_email(subject, body, max_words)
    logger.info("node=validate_email errors=%s", errors)
    return {"validation_errors": errors}


async def check_deliverability_node(
    state: OutreachState,
    checker: DeliverabilityChecker,
    settings: Settings,
) -> dict[str, Any]:
    """Gate on SPF/DKIM snapshot for the sending domain."""
    if not settings.agent.require_deliverability_check:
        logger.info("node=check_deliverability skipped")
        return {
            "deliverability_ok": True,
            "deliverability_details": {"skipped": True},
        }
    domain = infer_sender_domain(state["sender_company"], settings.agent.sender_domain)
    details = await checker.check_domain(domain)
    logger.info("node=check_deliverability domain=%s ok=%s", domain, details.get("ok"))
    return {"deliverability_ok": bool(details.get("ok")), "deliverability_details": details}


def decide(state: OutreachState, settings: Settings) -> dict[str, Any]:
    """Deterministic policy — no LLM here."""
    if state.get("validation_errors"):
        decision, reason = "reject", "validation failed"
    elif settings.agent.require_deliverability_check and not state.get("deliverability_ok"):
        decision, reason = "hold", "deliverability issues"
    elif settings.agent.require_human_approval:
        decision, reason = "hold", "awaiting approval"
    else:
        decision, reason = "send", "all checks passed"
    logger.info("node=decide decision=%s reason=%s", decision, reason)
    return {"decision": decision, "decision_reason": reason}


async def save_draft_node(state: OutreachState, draft_service: EmailDraftService) -> dict[str, Any]:
    """Persist the draft for audit even when we reject or hold."""
    subject = (state.get("email_subject") or "Outreach draft").strip() or "Outreach draft"
    body = (state.get("email_body") or "(empty — generation failed)").strip()
    logger.info("node=save_draft decision=%s", state.get("decision"))
    draft = await draft_service.create(
        EmailDraftCreate(
            person_id=state["person_id"],
            subject=subject[:500],
            body=body,
            goal=_goal(state["goal"]),
            generation_context={
                "decision": state.get("decision"),
                "decision_reason": state.get("decision_reason"),
                "rag_context_used": state.get("rag_context") or [],
                "validation_errors": state.get("validation_errors") or [],
                "deliverability": state.get("deliverability_details"),
                "tokens_input": state.get("total_tokens_input"),
                "tokens_output": state.get("total_tokens_output"),
                "estimated_cost_usd": state.get("total_cost_usd"),
                "iteration": state.get("iteration"),
            },
        )
    )
    return {"draft_id": draft.id}


async def save_and_send_node(state: OutreachState, draft_service: EmailDraftService) -> dict[str, Any]:
    """Save, then stub-mark sent. Real SMTP lands in Day 10."""
    update = await save_draft_node(state, draft_service)
    draft_id: UUID | None = update.get("draft_id")
    if draft_id is not None:
        await draft_service.mark_sent(draft_id)
        logger.info("node=save_and_send stub mark_sent draft_id=%s", draft_id)
    return update


def _goal(value: str) -> EmailGoal:
    try:
        return EmailGoal(value)
    except ValueError:
        return EmailGoal.MEETING
