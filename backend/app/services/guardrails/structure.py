"""Cold-email shape: greeting, CTA, no templates, sane length."""

from __future__ import annotations

import re
from typing import Any

from app.services.guardrails.base import BaseGuardrail, GuardrailResult

_CTA = (
    "would you be open",
    "are you free",
    "let's",
    "lets ",
    "do you have",
    "would you like",
    "interested in",
    "would you have",
    "15 minutes",
    "compare notes",
)
_BANAL = "i hope this email finds you well"
_PLACEHOLDER = re.compile(r"\[your name\]|\{\{.+?\}\}|\{[a-z_]+\}", re.IGNORECASE)


class StructureGuardrail(BaseGuardrail):
    """Structural hygiene for a first-touch email."""

    name = "structure"

    async def check(self, content: str, context: dict[str, Any] | None = None) -> GuardrailResult:
        body = content or ""
        missing: list[str] = []
        severity = "info"
        passed = True
        reason: str | None = None

        person = (context or {}).get("person") or (context or {}).get("person_data") or {}
        first = ""
        if isinstance(person, dict):
            first = str(person.get("first_name") or "")
        head = body[:50]
        if first and first.lower() not in head.lower():
            missing.append("greeting")
            severity = "warning"
            reason = "no recipient name in the opening"

        lower = body.lower()
        if not any(cta in lower for cta in _CTA):
            missing.append("cta")
            severity = "error"
            passed = False
            reason = "missing call to action"

        if _BANAL in lower:
            missing.append("banality")
            if severity not in {"error", "critical"}:
                severity = "warning"
            reason = reason or "cliché opener"

        if _PLACEHOLDER.search(body):
            missing.append("placeholder")
            severity = "error"
            passed = False
            reason = "unresolved template placeholder"

        words = [w for w in body.split() if w]
        n = len(words)
        if n < 50 or n > 200:
            missing.append("length")
            if severity not in {"error", "critical"}:
                severity = "warning"
            reason = reason or f"word count {n} outside 50-200"

        paras = [p for p in re.split(r"\n\s*\n", body.strip()) if p.strip()]
        if paras and not (2 <= len(paras) <= 4):
            missing.append("paragraphs")
            if severity not in {"error", "critical"}:
                severity = "warning"
            reason = reason or f"paragraph count {len(paras)} outside 2-4"

        if not missing:
            return GuardrailResult(passed=True, severity="info", metadata={"missing_sections": []}, name=self.name)
        return GuardrailResult(
            passed=passed,
            reason=reason,
            severity=severity,
            metadata={"missing_sections": missing, "word_count": n, "paragraphs": len(paras) or 1},
            name=self.name,
        )
