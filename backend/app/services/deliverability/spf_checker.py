"""SPF (RFC 7208) TXT parse — one record, lookup budget, all qualifier."""

from __future__ import annotations

import re
from typing import Any

from app.services.deliverability.dns_resolver import DNSResolver

_ALL_RE = re.compile(r"([+\-~?]?)all\b", re.IGNORECASE)


class SPFChecker:
    def __init__(self, resolver: DNSResolver) -> None:
        self.resolver = resolver

    async def check(self, domain: str) -> dict[str, Any]:
        txts = await self.resolver.resolve_txt(domain)
        spf_records = [item.strip() for item in txts if item.strip().lower().startswith("v=spf1")]
        if not spf_records:
            return {
                "valid": False,
                "record": None,
                "reason": "No SPF record found",
                "policy": None,
                "mechanisms": [],
                "lookup_count": 0,
                "warnings": [],
            }
        if len(spf_records) > 1:
            return {
                "valid": False,
                "record": " | ".join(spf_records),
                "reason": "Multiple SPF records",
                "policy": None,
                "mechanisms": [],
                "lookup_count": 0,
                "warnings": ["RFC 7208 allows only one SPF TXT record"],
            }

        record = spf_records[0]
        mechanisms = _mechanisms(record)
        lookup_count = _lookup_count(mechanisms)
        warnings: list[str] = []
        if lookup_count > 10:
            warnings.append("SPF DNS lookup limit exceeded (max 10 include/a/mx/ptr/exists/redirect)")
        policy = _policy(record)
        return {
            "valid": True,
            "record": record,
            "policy": policy,
            "mechanisms": mechanisms,
            "lookup_count": lookup_count,
            "warnings": warnings,
            "reason": None,
        }


def _mechanisms(record: str) -> list[str]:
    parts = record.split()
    return [part for part in parts[1:] if part]


def _lookup_count(mechanisms: list[str]) -> int:
    count = 0
    for mech in mechanisms:
        lowered = mech.lower().lstrip("+-~?")
        if lowered.startswith("include:") or lowered.startswith("exists:") or lowered.startswith("redirect="):
            count += 1
            continue
        token = lowered.split(":", 1)[0].split("/", 1)[0]
        if token in {"a", "mx", "ptr"}:
            count += 1
    return count


def _policy(record: str) -> str:
    matches = _ALL_RE.findall(record)
    if not matches:
        return "unknown"
    qualifier = matches[-1]
    mapping = {"": "pass", "+": "pass", "-": "hardfail", "~": "softfail", "?": "neutral"}
    return mapping.get(qualifier, "unknown")
