"""Toxicity, politics, spam, and shady-link heuristics for outbound copy."""

from __future__ import annotations

import re
from typing import Any

from app.services.guardrails.base import BaseGuardrail, GuardrailResult

# Explicit policy terms — keep the list small and auditable (not a slur dump).
_CRITICAL = (
    "kill yourself",
    "you are worthless",
    "racial inferior",
    "gas the",
)

_POLITICAL = (
    "democrat",
    "republican",
    "liberal elite",
    "sharia",
    "jihad",
    "evangelical vote",
)

_SPAM = (
    "act now",
    "urgent",
    "limited time",
    "guarantee",
    "100% free",
    "risk-free",
    "no obligation",
    "click here",
)

_SHORTENERS = ("bit.ly", "tinyurl", "t.co/", "goo.gl", "ow.ly")
_CAPS = re.compile(r"\b[A-Z]{5,}\b")
_BANGS = re.compile(r"!{4,}")


class ContentPolicyGuardrail(BaseGuardrail):
    """Block abuse; warn on politics, spam phrasing, ALL CAPS, and URL shorteners."""

    name = "content_policy"

    async def check(self, content: str, context: dict[str, Any] | None = None) -> GuardrailResult:
        _ = context
        text = content or ""
        lower = text.lower()
        triggered: list[str] = []
        severity = "info"
        passed = True
        reason: str | None = None

        for phrase in _CRITICAL:
            if phrase in lower:
                triggered.append(f"critical:{phrase}")
                severity = "critical"
                passed = False
                reason = "content policy violation"

        for phrase in _POLITICAL:
            if phrase in lower:
                triggered.append(f"political:{phrase}")
                if severity not in {"critical", "error"}:
                    severity = "warning"
                    reason = reason or "political or religious language"

        for phrase in _SPAM:
            if phrase in lower:
                triggered.append(f"spam:{phrase}")
                if severity not in {"critical", "error"}:
                    severity = "warning"
                    reason = reason or "spam trigger phrasing"

        if _CAPS.search(text):
            triggered.append("caps_lock_word")
            if severity not in {"critical", "error"}:
                severity = "warning"
                reason = reason or "shouting (ALL CAPS)"

        if _BANGS.search(text):
            triggered.append("repeated_exclamation")
            if severity not in {"critical", "error"}:
                severity = "warning"
                reason = reason or "excessive exclamation"

        for host in _SHORTENERS:
            if host in lower:
                triggered.append(f"shortener:{host}")
                if severity not in {"critical", "error"}:
                    severity = "warning"
                    reason = reason or "URL shortener (deliverability / phishing risk)"

        return GuardrailResult(
            passed=passed,
            reason=reason,
            severity=severity if triggered else "info",
            metadata={"triggered_rules": triggered},
            name=self.name,
        )
