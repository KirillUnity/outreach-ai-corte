"""Heuristic hallucination check — no NER model (8 GB RAM, no local neural nets)."""

from __future__ import annotations

import re
from typing import Any

from app.services.guardrails.base import BaseGuardrail, GuardrailResult

_TOKEN = re.compile(r"\b[A-Z][A-Za-z]{3,}\b")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")

_STOP = frozenset(
    {
        "this",
        "that",
        "these",
        "those",
        "with",
        "from",
        "your",
        "their",
        "have",
        "been",
        "will",
        "would",
        "could",
        "should",
        "about",
        "after",
        "before",
        "next",
        "week",
        "month",
        "year",
        "team",
        "founders",
        "founder",
        "minutes",
        "quick",
        "idea",
        "hello",
        "thanks",
        "regards",
        "best",
        "please",
        "looking",
        "forward",
        "compare",
        "notes",
        "noticed",
        "investing",
        "better",
        "workflows",
        "help",
        "founders",
        "spend",
        "outreach",
        "research",
        "january",
        "february",
        "march",
        "april",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    }
)


class HallucinationGuardrail(BaseGuardrail):
    """Flag proper-noun-like tokens that never appear in RAG / person / company context."""

    name = "hallucination"

    async def check(self, content: str, context: dict[str, Any] | None = None) -> GuardrailResult:
        entities = self._extract_entities(content)
        allowed = self._allowed_tokens(context or {})
        blob = self._normalize(self._context_blob(context or {}))
        unknown = sorted(
            entity
            for entity in entities
            if entity not in allowed and entity not in blob and entity not in _STOP
        )
        if len(unknown) > 3:
            return GuardrailResult(
                passed=False,
                reason=f"{len(unknown)} unknown entities (possible hallucination)",
                severity="error",
                metadata={"unknown_entities": unknown},
                name=self.name,
            )
        if unknown:
            return GuardrailResult(
                passed=True,
                reason="potential hallucination",
                severity="warning",
                metadata={"unknown_entities": unknown},
                name=self.name,
            )
        return GuardrailResult(passed=True, severity="info", metadata={"unknown_entities": []}, name=self.name)

    def _extract_entities(self, text: str) -> set[str]:
        """Capitalized tokens longer than 3 letters, skipping sentence-initial words."""
        found: set[str] = set()
        for sentence in _SENTENCE.split(text or "") or [text or ""]:
            words = sentence.split()
            for index, word in enumerate(words):
                match = _TOKEN.search(word)
                if not match:
                    continue
                if index == 0:
                    continue
                token = self._normalize(match.group(0))
                if len(token) > 3 and token not in _STOP:
                    found.add(token)
        return found

    def _normalize(self, text: str) -> str:
        return (text or "").strip().lower()

    def _context_blob(self, context: dict[str, Any]) -> str:
        parts: list[str] = []
        person = context.get("person") or context.get("person_data") or {}
        company = context.get("company") or context.get("company_data") or {}
        if isinstance(person, dict):
            parts.extend(str(v) for v in person.values() if v)
        if isinstance(company, dict):
            parts.extend(str(v) for v in company.values() if v)
        rag = context.get("rag_context") or []
        if isinstance(rag, list):
            parts.extend(str(item) for item in rag)
        else:
            parts.append(str(rag))
        for key in ("sender_name", "sender_title", "sender_company", "sender_email"):
            if context.get(key):
                parts.append(str(context[key]))
        return " ".join(parts)

    def _allowed_tokens(self, context: dict[str, Any]) -> set[str]:
        blob = self._context_blob(context)
        return {self._normalize(m.group(0)) for m in _TOKEN.finditer(blob)} | {
            self._normalize(w) for w in blob.replace(".", " ").split() if len(w) > 3
        }
