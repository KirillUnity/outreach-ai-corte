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
from app.services.prompt_ab import PromptABTester, default_prompt_ab, suffix_for
from app.services.cost_tracker import CostTracker
from app.services.guardrails.pipeline import GuardrailPipeline, build_default_pipeline, results_as_dicts
from app.services.llm_client import LLMClient
from app.services.output_validator import SPAM_WORDS, OutputValidator
from app.services.prompts.email_prompts import (
    GUARDRAIL_RETRY_SUFFIX,
    SYSTEM_PROMPT_OUTREACH,
    USER_PROMPT_TEMPLATE,
    USER_PROMPT_WITH_WARM_INTRO,
    VALIDATION_RETRY_SUFFIX,
)
from app.services.rag_service import RAGService
from app.services.tracing import TracingService, get_tracing

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
        tracing: TracingService | None = None,
        guardrail_pipeline: GuardrailPipeline | None = None,
        ab_tester: PromptABTester | None = None,
    ) -> None:
        self.settings = settings or default_settings
        self.cost_tracker = cost_tracker or CostTracker()
        self.tracing = tracing if tracing is not None else get_tracing()
        self.llm_client = llm_client or LLMClient(
            self.settings, cost_tracker=self.cost_tracker, tracing=self.tracing
        )
        self.rag_service = rag_service or RAGService(self.settings)
        self.validator = validator or OutputValidator()
        from app.services.agent.scoring import QualityScorer

        self.scorer = QualityScorer()
        self.guardrail_pipeline = guardrail_pipeline or build_default_pipeline()
        if ab_tester is not None:
            self.ab_tester = ab_tester
        elif self.settings.prompt_ab.enabled:
            self.ab_tester = default_prompt_ab()
        else:
            self.ab_tester = None

    async def generate(
        self,
        person: Person,
        company: Company | None,
        request: EmailGenerationRequest,
        graph_context: dict[str, Any] | None = None,
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
        variant = "v1_default"
        if self.ab_tester is not None:
            variant = self.ab_tester.pick_variant()
            system = system + suffix_for(variant)
        extra_meta = {"prompt_variant": variant}
        user = self._render_user_prompt(
            person, company, request, rag_context, graph_context=graph_context
        )

        result = await self.llm_client.chat_json(system, user, extra_metadata=extra_meta)
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
            result = await self.llm_client.chat_json(system, retry_user, extra_metadata=extra_meta)
            subject, body = self._extract_email(result["parsed"])
            valid, errors = self.validator.validate_email(subject, body, request.max_words)

        guard_ctx = self._guardrail_context(person, company, rag_context, request)
        passed, rail_results = await self.guardrail_pipeline.run_all(
            f"{subject}\n{body}", guard_ctx
        )
        if not passed:
            reasons = [r.reason or r.name for r in self.guardrail_pipeline.get_blockers(rail_results)]
            logger.warning("guardrails blocked person=%s reasons=%s", person.id, reasons)
            retried = True
            retry_user = (
                f"{user}\n\n"
                + GUARDRAIL_RETRY_SUFFIX.format(reasons="; ".join(reasons) or "policy")
            )
            result = await self.llm_client.chat_json(system, retry_user, extra_metadata=extra_meta)
            subject, body = self._extract_email(result["parsed"])
            valid, errors = self.validator.validate_email(subject, body, request.max_words)
            passed, rail_results = await self.guardrail_pipeline.run_all(
                f"{subject}\n{body}", guard_ctx
            )

        record = self.cost_tracker.records[-1] if self.cost_tracker.records else None
        scores = self.scorer.score_email(
            subject,
            body,
            recipient_name=person.first_name or "",
            company_name=company.name if company is not None else "",
            draft_id=str(person.id),
        )
        self.tracing.log_scores(draft_id=str(person.id), scores=scores)
        if self.ab_tester is not None:
            personal = float(scores.get("personalization_score") or 0.0)
            self.ab_tester.log_result(variant, success=passed, score=personal)

        decision = "reject" if not passed else None
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
            "quality_scores": scores,
            "guardrail_results": results_as_dicts(rail_results),
            "guardrails_passed": passed,
            "decision": decision,
            "prompt_variant": variant,
            "graph_context": graph_context or {},
        }

    def _guardrail_context(
        self,
        person: Person,
        company: Company | None,
        rag_context: str,
        request: EmailGenerationRequest,
    ) -> dict[str, Any]:
        return {
            "person": {
                "first_name": person.first_name,
                "last_name": person.last_name,
                "title": person.title,
                "email": person.email,
            },
            "company": {
                "name": company.name if company is not None else "",
                "domain": company.domain if company is not None else "",
            },
            "rag_context": rag_context,
            "sender_name": request.sender_name,
            "sender_title": request.sender_title,
            "sender_company": request.sender_company,
            "sender_email": "",
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
        graph_context: dict[str, Any] | None = None,
    ) -> str:
        extra = ""
        if request.custom_instructions:
            extra = f"ADDITIONAL INSTRUCTIONS:\n{request.custom_instructions}"
        if graph_context and graph_context.get("email_found") and graph_context.get("email_address"):
            email_hint = f"Recipient email: {graph_context['email_address']}"
        else:
            email_hint = "Recipient email: not found — email will need manual lookup"
        if person.email and email_hint.startswith("Recipient email: not found"):
            email_hint = f"Recipient email: {person.email}"
        mutual = self._mutual_connection_name(person, graph_context)
        template = USER_PROMPT_WITH_WARM_INTRO if mutual else USER_PROMPT_TEMPLATE
        payload = {
            "first_name": person.first_name,
            "last_name": person.last_name,
            "title": person.title or "unknown",
            "company_name": company.name if company is not None else "unknown",
            "email_hint": email_hint,
            "rag_context": rag_context,
            "goal_description": GOAL_DESCRIPTIONS.get(request.goal, request.goal.value),
            "tone": request.tone,
            "sender_name": request.sender_name,
            "sender_title": request.sender_title,
            "sender_company": request.sender_company,
            "custom_instructions": extra,
        }
        if mutual:
            payload["mutual_connection_name"] = mutual
        return template.format(**payload)

    @staticmethod
    def _mutual_connection_name(
        person: Person,
        graph_context: dict[str, Any] | None,
    ) -> str | None:
        if not graph_context or not graph_context.get("warm_intro_available"):
            return None
        via = str(graph_context.get("warm_intro_via") or "").strip()
        recipient = f"{person.first_name or ''} {person.last_name or ''}".strip().lower()
        hops = graph_context.get("warm_intro_path") or []
        if not via and isinstance(hops, list):
            for hop in reversed(hops):
                if not isinstance(hop, dict):
                    continue
                name = str(hop.get("name") or "").strip()
                if name and name.lower() != recipient:
                    via = name
                    break
        if not via:
            names = str(graph_context.get("warm_intro_names") or "").strip()
            if names and names.lower() != "a mutual connection":
                via = names.split(",")[0].strip()
        if not via or via.lower() == recipient:
            return None
        return via

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
