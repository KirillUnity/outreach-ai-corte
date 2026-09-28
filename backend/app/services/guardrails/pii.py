"""Detect accidental PII in outbound drafts (regex only — no cloud PII API)."""

from __future__ import annotations

import re
from typing import Any

from app.services.guardrails.base import BaseGuardrail, GuardrailResult

_PHONE = re.compile(r"\+?\d[\d\s\-\(\)]{8,}\d")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_CARD = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


class PIIGuardrail(BaseGuardrail):
    """Fail closed on phones, extra emails, PAN-like digits, US SSN. Sender email is allowed."""

    name = "pii_detection"

    async def check(self, content: str, context: dict[str, Any] | None = None) -> GuardrailResult:
        text = content or ""
        sender = self._sender_email(context or {})
        found: dict[str, int] = {}

        phones = _PHONE.findall(text)
        if phones:
            found["phone"] = len(phones)

        emails = [m.group(0) for m in _EMAIL.finditer(text)]
        extras = [e for e in emails if e.lower() != sender]
        if extras:
            found["email"] = len(extras)

        if _CARD.search(text):
            found["credit_card"] = len(_CARD.findall(text))
        if _SSN.search(text):
            found["ssn"] = len(_SSN.findall(text))

        if found:
            return GuardrailResult(
                passed=False,
                reason="possible PII in outbound copy",
                severity="error",
                metadata={"pii_types": found},
                name=self.name,
            )
        return GuardrailResult(passed=True, severity="info", metadata={"pii_types": {}}, name=self.name)

    def _sender_email(self, context: dict[str, Any]) -> str:
        return str(context.get("sender_email") or "").lower()
