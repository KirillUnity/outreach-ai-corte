"""DKIM TXT at {selector}._domainkey.{domain}."""

from __future__ import annotations

import base64
import re
from typing import Any

from app.services.deliverability.dns_resolver import DNSResolver

_TAG_RE = re.compile(r"([a-z]+)=([^;]*)", re.IGNORECASE)


class DKIMChecker:
    def __init__(self, resolver: DNSResolver, selectors: list[str]) -> None:
        self.resolver = resolver
        self.selectors = list(selectors)

    async def check(self, domain: str) -> dict[str, Any]:
        tried: list[str] = []
        for selector in self.selectors:
            tried.append(selector)
            name = f"{selector}._domainkey.{domain}"
            txts = await self.resolver.resolve_txt(name)
            for raw in txts:
                looks_dkim = "v=DKIM1" in raw.upper() or "p=" in raw.lower()
                if not looks_dkim:
                    continue
                parsed = self._parse_dkim_record(raw)
                if parsed.get("revoked"):
                    return {
                        "valid": False,
                        "selector": selector,
                        "record": raw,
                        "key_type": parsed.get("key_type"),
                        "key_length": parsed.get("key_length"),
                        "tried_selectors": tried,
                        "reason": "DKIM public key revoked (empty p=)",
                    }
                if parsed.get("public_key"):
                    return {
                        "valid": True,
                        "selector": selector,
                        "record": raw,
                        "key_type": parsed.get("key_type") or "rsa",
                        "key_length": parsed.get("key_length"),
                        "tried_selectors": tried,
                        "reason": None,
                    }
        return {
            "valid": False,
            "selector": None,
            "record": None,
            "key_type": None,
            "key_length": None,
            "tried_selectors": tried,
            "reason": "No DKIM record found in common selectors",
        }

    def _parse_dkim_record(self, record: str) -> dict[str, Any]:
        tags = {match.group(1).lower(): match.group(2).strip() for match in _TAG_RE.finditer(record)}
        key_type = (tags.get("k") or "rsa").lower()
        public = tags.get("p", "")
        if "p=" in record.lower() and public == "":
            return {"revoked": True, "key_type": key_type, "key_length": None, "public_key": None}
        if not public:
            return {"revoked": False, "key_type": key_type, "key_length": None, "public_key": None}
        key_length = _rsa_bit_length(public) if key_type == "rsa" else (256 if key_type == "ed25519" else None)
        return {
            "revoked": False,
            "key_type": key_type,
            "key_length": key_length,
            "public_key": public,
        }


def _rsa_bit_length(b64_key: str) -> int | None:
    try:
        padding = "=" * (-len(b64_key) % 4)
        raw = base64.b64decode(b64_key + padding)
        return len(raw) * 8
    except Exception:
        return None
