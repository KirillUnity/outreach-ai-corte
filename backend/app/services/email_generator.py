"""Generate a personalized cold email from person + RAG company context."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.config import Settings, settings as default_settings
from app.models.company import Company
from app.models.enums import EmailGoal
from app.models.person import Person
from app.schemas.email_draft import EmailGenerationRequest
from app.services.cost_tracker import CostTracker
from app.services.llm_client import LLMClient
from app.services.output_validator import SPAM_WORDS, OutputValidator
from app.services.prompts.email_prompts import (
    SYSTEM_PROMPT_OUTREACH,
    USER_PROMPT_TEMPLATE,
    VALIDATION_RETRY_SUFFIX,
)
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

GOAL_DESCRIPTIONS: dict[EmailGoal, str] = {
    EmailGoal.MEETING: "book a 15-minute intro call",
    EmailGoal.INTRO: "introduce the sender and open a conversation",
    EmailGoal.FOLLOW_UP: "follow up on a previous touch without sounding pushy",
    EmailGoal.DEMO: "invite the recipient to a short product walkthrough",
    EmailGoal.NURTURE: "share one useful observation and stay on their radar",
    EmailGoal.BREAKUP: "close the thread politely if now is not the right time",
}

_SPAM_RE = re.compile("|".join(re.escape(word) for word in SPAM_WORDS), re.IGNORECASE)


class EmailGenerator:
    """RAG retrieve → prompt → LLM JSON → validate (one retry) → metadata."""

    def __init__(
        self,
        settings: Settings | None = None,
        llm_client: LLMClient | None = None,
        rag_service: RAGService | None = None,
        cost_tracker: CostTracker | None = None,
        validator: OutputValidator | None = None,
    ) -> None:
        self.settings = settings or default_settings
        self.cost_tracker = cost_tracker or CostTracker()
        self.llm_client = llm_client or LLMClient(self.settings, cost_tracker=self.cost_tracker)
        self.rag_service = rag_service or RAGService(self.settings)
        self.validator = validator or OutputValidator()

    async def generate(
        self,
        person: Person,
        company: Company | None,
        request: EmailGenerationRequest,
    ) -> dict[str, Any]:
        """Return subject/body plus RAG chunks and token cost."""
        rag_chunks = await self._load_rag_chunks(person, company, request)
        rag_context = (
            "\n\n".join(f"[{index + 1}] {text}" for index, text in enumerate(rag_chunks))
            if rag_chunks
            else "No indexed company research yet. Do not invent company facts."
        )
        system = SYSTEM_PROMPT_OUTREACH.format(
            max_words=request.max_words,
            language=request.language,
        )
        user = self._render_user_prompt(person, company, request, rag_context)

        result = await self.llm_client.chat_json(system, user)
        subject, body = self._extract_email(result["parsed"])
        valid, errors = self.validator.validate_email(subject, body, request.max_words)
        retried = False
        if not valid or self._contains_spam_words(body) or self._contains_spam_words(subject):
            retried = True
            retry_user = (
                f"{user}\n\n"
                + VALIDATION_RETRY_SUFFIX.format(errors="; ".join(errors) or "spam trigger words")
            )
            logger.info("email regen person=%s errors=%s", person.id, errors)
            result = await self.llm_client.chat_json(system, retry_user)
            subject, body = self._extract_email(result["parsed"])
            valid, errors = self.validator.validate_email(subject, body, request.max_words)

        record = self.cost_tracker.records[-1] if self.cost_tracker.records else None
        return {
            "subject": subject[:200],
            "body": body,
            "rag_context_used": rag_chunks,
            "tokens_input": int(result["tokens_input"]),
            "tokens_output": int(result["tokens_output"]),
            "estimated_cost_usd": record.estimated_cost_usd if record else 0.0,
            "model": result["model"],
            "validation_errors": [] if valid else errors,
            "retried": retried,
        }

    async def _load_rag_chunks(
        self,
        person: Person,
        company: Company | None,
        request: EmailGenerationRequest,
    ) -> list[str]:
        if company is None or not company.raw_site_text:
            return []
        query = self._build_search_query(person, request, company)
        try:
            hits = await self.rag_service.search(company.domain, query, top_k=5)
        except Exception:
            logger.exception("RAG search failed domain=%s", company.domain)
            return []
        return [str(hit.get("text") or "") for hit in hits if hit.get("text")]

    def _render_user_prompt(
        self,
        person: Person,
        company: Company | None,
        request: EmailGenerationRequest,
        rag_context: str,
    ) -> str:
        extra = ""
        if request.custom_instructions:
            extra = f"ADDITIONAL INSTRUCTIONS:\n{request.custom_instructions}"
        return USER_PROMPT_TEMPLATE.format(
            first_name=person.first_name,
            last_name=person.last_name,
            title=person.title or "unknown",
            company_name=company.name if company is not None else "unknown",
            rag_context=rag_context,
            goal_description=GOAL_DESCRIPTIONS.get(request.goal, request.goal.value),
            tone=request.tone,
            sender_name=request.sender_name,
            sender_title=request.sender_title,
            sender_company=request.sender_company,
            custom_instructions=extra,
        )

    def _build_search_query(
        self,
        person: Person,
        request: EmailGenerationRequest,
        company: Company | None = None,
    ) -> str:
        """Blend role, company, goal, and any extra instructions for Chroma."""
        parts = [
            person.title or "",
            company.name if company is not None else "",
            GOAL_DESCRIPTIONS.get(request.goal, request.goal.value),
            request.custom_instructions or "",
        ]
        return " ".join(part.strip() for part in parts if part and part.strip())

    def _contains_spam_words(self, text: str) -> bool:
        """Case-insensitive check against the shared spam list."""
        return bool(_SPAM_RE.search(text or ""))

    @staticmethod
    def _extract_email(parsed: dict[str, Any]) -> tuple[str, str]:
        subject = str(parsed.get("subject") or "").strip()
        body = str(parsed.get("body") or "").strip()
        if not subject or not body:
            raise ValueError("LLM JSON must include non-empty subject and body")
        if len(body) > 10_000:
            raise ValueError("LLM body is unreasonably long")
        return subject, body
