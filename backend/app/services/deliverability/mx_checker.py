"""MX lookup and coarse mailbox-provider guess."""

from __future__ import annotations

from typing import Any

from app.services.deliverability.dns_resolver import DNSResolver


class MXChecker:
    def __init__(self, resolver: DNSResolver) -> None:
        self.resolver = resolver

    async def check(self, domain: str) -> dict[str, Any]:
        records = await self.resolver.resolve_mx(domain)
        if not records:
            return {
                "valid": False,
                "records": [],
                "provider": "unknown",
                "reason": "No MX records",
            }
        return {
            "valid": True,
            "records": records,
            "provider": self._detect_provider(records),
            "reason": None,
        }

    def _detect_provider(self, mx_records: list[dict[str, Any]]) -> str:
        blob = " ".join(str(row.get("exchange") or "").lower() for row in mx_records)
        if "google" in blob or "gmail" in blob:
            return "google"
        if "outlook" in blob or "microsoft" in blob or "protection.outlook" in blob:
            return "microsoft"
        if "yandex" in blob:
            return "yandex"
        return "unknown"
