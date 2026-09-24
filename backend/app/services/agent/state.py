"""LangGraph state for one outreach run."""

from __future__ import annotations

from operator import add
from typing import Annotated, NotRequired, TypedDict
from uuid import UUID


class OutreachState(TypedDict):
    """State that flows through every node. List fields use the `add` reducer."""

    person_id: UUID
    goal: str
    sender_name: str
    sender_title: str
    sender_company: str
    language: str
    max_words: int

    person_data: NotRequired[dict | None]
    company_data: NotRequired[dict | None]
    company_researched: NotRequired[bool]
    rag_context: NotRequired[list[str] | None]
    email_subject: NotRequired[str | None]
    email_body: NotRequired[str | None]
    deliverability_ok: NotRequired[bool | None]
    deliverability_details: NotRequired[dict | None]
    # Overwrite (not `add`): a successful regen must clear the previous failures.
    validation_errors: NotRequired[list[str]]

    draft_id: NotRequired[UUID | None]
    decision: NotRequired[str | None]
    decision_reason: NotRequired[str | None]

    iteration: int
    total_tokens_input: int
    total_tokens_output: int
    total_cost_usd: float
    errors: Annotated[list[str], add]
