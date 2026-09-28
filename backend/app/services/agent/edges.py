"""Conditional routers — names only, no I/O."""

from __future__ import annotations

from app.services.agent.state import OutreachState


def route_after_load(state: OutreachState) -> str:
    """Stop the graph if the person (or another load error) is missing."""
    if state.get("errors"):
        return "fail"
    return "research_company"


def route_after_validate(state: OutreachState) -> str:
    """One regenerate, then continue even if the draft is still dirty."""
    blockers = [
        row
        for row in (state.get("guardrail_results") or [])
        if isinstance(row, dict)
        and not row.get("passed")
        and row.get("severity") in {"error", "critical"}
    ]
    dirty = bool(state.get("validation_errors")) or bool(blockers)
    if dirty and int(state.get("iteration") or 0) < 2:
        return "generate_email"
    return "check_deliverability"


def route_after_decide(state: OutreachState) -> str:
    """Send only on an explicit send; hold/reject still persist a draft."""
    if state.get("decision") == "send":
        return "save_and_send"
    return "save_draft"
