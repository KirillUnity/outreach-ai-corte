"""Post-generation checks for cold-email copy."""

from __future__ import annotations

import re
import unicodedata

SPAM_WORDS = (
    "free",
    "guarantee",
    "act now",
    "limited time",
    "click here",
    "buy now",
    "risk-free",
)

FORBIDDEN_PHRASES = ("i hope this email finds you well",)

_INVISIBLE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")
_SPAM_RE = re.compile("|".join(re.escape(word) for word in SPAM_WORDS), re.IGNORECASE)
_ALL_CAPS_WORD = re.compile(r"\b[A-Z]{4,}\b")


class OutputValidator:
    """Heuristic validator — not a spam filter, just a last-mile sanity check."""

    def validate_email(self, subject: str, body: str, max_words: int) -> tuple[bool, list[str]]:
        """Return (is_valid, errors) for a generated subject + body."""
        errors: list[str] = []
        if not (subject or "").strip():
            errors.append("subject is empty")
        elif len(subject) > 200:
            errors.append("subject exceeds 200 characters")
        elif "\n" in subject:
            errors.append("subject contains a newline")

        if not (body or "").strip():
            errors.append("body is empty")
        elif len(body) > max_words * 8:
            errors.append("body exceeds length heuristic")

        combined = f"{subject}\n{body}"
        if _SPAM_RE.search(combined):
            errors.append("contains spam trigger words")
        if _ALL_CAPS_WORD.search(combined):
            errors.append("contains ALL CAPS words")
        lowered = combined.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                errors.append(f"contains forbidden phrase: {phrase}")
        if _INVISIBLE.search(combined) or any(unicodedata.category(ch) == "Cf" for ch in combined):
            errors.append("contains invisible characters")

        return (not errors, errors)
