"""DMARC TXT at _dmarc.{domain} (RFC 7489)."""

from __future__ import annotations

import re
from typing import Any

from app.services.deliverability.dns_resolver import DNSResolver

_TAG_RE = re.compile(r"([a-z]+)=([^;]*)", re.IGNORECASE)


class DMARCChecker:
    def __init__(self, resolver: DNSResolver) -> None:
        self.resolver = resolver

    async def check(self, domain: str) -> dict[str, Any]:
        txts = await self.resolver.resolve_txt(f"_dmarc.{domain}")
        records = [
            item.strip() for item in txts if "v=dmarc1" in item.replace(" ", "").lower()
        ]
        if not records:
            return {
                "valid": False,
                "record": None,
                "policy": None,
                "subdomain_policy": None,
                "rua": [],
                "pct": None,
                "warnings": [],
                "reason": "No DMARC record",
            }
        record = records[0]
        tags = {match.group(1).lower(): match.group(2).strip() for match in _TAG_RE.finditer(record)}
        policy = (tags.get("p") or "").lower() or None
        subdomain = (tags.get("sp") or "").lower() or None
        rua = [part.strip() for part in (tags.get("rua") or "").split(",") if part.strip()]
        pct_raw = tags.get("pct")
        pct = int(pct_raw) if pct_raw and pct_raw.isdigit() else 100
        warnings: list[str] = []
        if policy == "none":
            warnings.append("DMARC p=none does not quarantine or reject failing mail")
        if not rua:
            warnings.append("DMARC rua missing — no aggregate reports")
        return {
            "valid": True,
            "record": record,
            "policy": policy,
            "subdomain_policy": subdomain,
            "rua": rua,
            "pct": pct,
            "warnings": warnings,
            "reason": None,
        }
