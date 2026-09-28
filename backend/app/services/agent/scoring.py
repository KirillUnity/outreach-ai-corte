"""Heuristic quality scores for generated outreach copy (no extra LLM call)."""

from __future__ import annotations

import re

from app.services.output_validator import SPAM_WORDS

_CTA = (
    "would you",
    "15 minutes",
    "fifteen minutes",
    "next week",
    "quick call",
    "intro call",
    "meet",
    "chat",
    "compare notes",
)

_SPAM_RE = re.compile("|".join(re.escape(word) for word in SPAM_WORDS), re.IGNORECASE)


class QualityScorer:
    """Cheap, deterministic scores — iterate prompts without waiting for replies."""

    def score_email(
        self,
        subject: str,
        body: str,
        *,
        recipient_name: str = "",
        company_name: str = "",
        draft_id: str | None = None,
    ) -> dict[str, float]:
        """Return 0..1 scores. `draft_id` is for Langfuse comments only."""
        _ = draft_id
        words = [w for w in (body or "").split() if w]
        n = len(words)
        if 80 <= n <= 120:
            length_score = 1.0
        elif n < 80:
            length_score = n / 80 if n else 0.0
        else:
            length_score = max(0.0, 1.0 - (n - 120) / 120)

        hits = len(_SPAM_RE.findall(f"{subject}\n{body}"))
        spam_score = max(0.0, 1.0 - 0.25 * hits)

        blob = f"{subject}\n{body}".lower()
        personalization = 0.0
        first = (recipient_name or "").strip().split()[:1]
        if first and first[0].lower() in blob:
            personalization += 0.5
        if (company_name or "").strip() and company_name.strip().lower() in blob:
            personalization += 0.5

        cta_score = 1.0 if any(phrase in blob for phrase in _CTA) else 0.0
        return {
            "length_score": round(length_score, 3),
            "spam_score": round(spam_score, 3),
            "personalization_score": round(personalization, 3),
            "cta_score": round(cta_score, 3),
        }
