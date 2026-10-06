"""Guess local-parts from first/last name + domain."""

from __future__ import annotations

import re
import unicodedata

_CONFIDENCE: dict[str, float] = {
    "{first}.{last}": 0.85,
    "{first}{last}": 0.75,
    "{f}{last}": 0.70,
    "{first}_{last}": 0.55,
    "{first}": 0.5,
}

_CYRILLIC = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


class PatternGenerator:
    def __init__(self, patterns: list[str]) -> None:
        self.patterns = list(patterns)

    def generate(self, first_name: str, last_name: str, domain: str) -> list[dict[str, object]]:
        first = self._normalize(first_name)
        last = self._normalize(last_name)
        host = (domain or "").strip().lower().lstrip("@")
        if not first or not last or not host:
            return []
        f_init = first[0]
        l_init = last[0]
        out: list[dict[str, object]] = []
        seen: set[str] = set()
        for pattern in self.patterns:
            local = (
                pattern.replace("{first}", first)
                .replace("{last}", last)
                .replace("{f}", f_init)
                .replace("{l}", l_init)
            )
            email = f"{local}@{host}"
            if email in seen:
                continue
            seen.add(email)
            out.append(
                {
                    "email": email,
                    "pattern": pattern,
                    "confidence": float(_CONFIDENCE.get(pattern, 0.4)),
                }
            )
        return out

    def _normalize(self, text: str) -> str:
        raw = self._transliterate((text or "").strip().lower())
        decomposed = unicodedata.normalize("NFKD", raw)
        stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
        return re.sub(r"[^a-z0-9-]+", "", stripped)

    def _transliterate(self, text: str) -> str:
        return "".join(_CYRILLIC.get(ch, ch) for ch in text)
