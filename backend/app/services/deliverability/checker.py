"""Fan-out SPF/DKIM/DMARC/MX and score the domain for outreach risk."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import Settings, settings as default_settings
from app.services.deliverability.dkim_checker import DKIMChecker
from app.services.deliverability.dmarc_checker import DMARCChecker
from app.services.deliverability.dns_resolver import DNSResolver
from app.services.deliverability.mx_checker import MXChecker
from app.services.deliverability.spf_checker import SPFChecker

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[datetime, dict[str, Any]]] = {}


def clear_deliverability_cache() -> None:
    """Drop in-process DNS check results (tests / TTL reset)."""
    _CACHE.clear()


class DeliverabilityChecker:
    """Live DNS checker. Distinct from `app.services.deliverability_checker` (DB snapshot gate)."""

    def __init__(self, settings: Settings | None = None, resolver: DNSResolver | None = None) -> None:
        self.settings = settings or default_settings
        self.resolver = resolver or DNSResolver(self.settings)
        self.spf = SPFChecker(self.resolver)
        self.dkim = DKIMChecker(self.resolver, self.settings.deliverability.dkim_selectors)
        self.dmarc = DMARCChecker(self.resolver)
        self.mx = MXChecker(self.resolver)

    async def check_domain(self, domain: str, use_cache: bool = True) -> dict[str, Any]:
        normalized = (domain or "").strip().lower()
        ttl = timedelta(seconds=self.settings.deliverability.cache_ttl_seconds)
        if use_cache:
            cached = _CACHE.get(normalized)
            if cached:
                ts, result = cached
                if datetime.now(timezone.utc) - ts < ttl:
                    logger.info("Cache hit for %s", normalized)
                    return result

        gathered = await asyncio.gather(
            self.spf.check(normalized),
            self.dkim.check(normalized),
            self.dmarc.check(normalized),
            self.mx.check(normalized),
            return_exceptions=True,
        )
        spf, dkim, dmarc, mx = (_as_dict(item, kind) for item, kind in zip(gathered, ("spf", "dkim", "dmarc", "mx"), strict=True))
        bundle = {"spf": spf, "dkim": dkim, "dmarc": dmarc, "mx": mx}
        score = self._compute_score(bundle)
        result = {
            "domain": normalized,
            "spf": spf,
            "dkim": dkim,
            "dmarc": dmarc,
            "mx": mx,
            "overall_score": score,
            "risk_level": self._classify_risk(score),
            "checked_at": datetime.now(timezone.utc),
            "recommendations": self._build_recommendations(bundle),
        }
        _CACHE[normalized] = (datetime.now(timezone.utc), result)
        return result

    def _compute_score(self, results: dict[str, Any]) -> int:
        score = 0
        if results.get("spf", {}).get("valid"):
            score += 25
        if results.get("dkim", {}).get("valid"):
            score += 25
        dmarc = results.get("dmarc") or {}
        if dmarc.get("valid"):
            policy = (dmarc.get("policy") or "").lower()
            if policy in {"quarantine", "reject"}:
                score += 30
            elif policy == "none":
                score += 15
        if results.get("mx", {}).get("valid"):
            score += 20
        return max(0, min(100, score))

    def _classify_risk(self, score: int) -> str:
        if score >= 80:
            return "low"
        if score >= 60:
            return "medium"
        if score >= 40:
            return "high"
        return "critical"

    def _build_recommendations(self, results: dict[str, Any]) -> list[str]:
        recs: list[str] = []
        if not results.get("spf", {}).get("valid"):
            recs.append("Add SPF record. Example: v=spf1 include:_spf.google.com ~all")
        if not results.get("dkim", {}).get("valid"):
            recs.append("Configure DKIM signing for your sending domain")
        dmarc = results.get("dmarc") or {}
        if not dmarc.get("valid"):
            recs.append("Publish a DMARC record at _dmarc.<domain> (start with p=none + rua)")
        elif (dmarc.get("policy") or "").lower() == "none":
            recs.append("Change DMARC policy to quarantine or reject after monitoring period")
        if not results.get("mx", {}).get("valid"):
            recs.append("Domain has no MX records — it can't receive replies")
        return recs


def _as_dict(item: object, kind: str) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    logger.warning("%s check failed: %s", kind, item)
    return {
        "valid": False,
        "reason": f"{kind} check failed: {item}",
        "record": None,
        "records": [],
        "warnings": [],
        "mechanisms": [],
        "rua": [],
        "tried_selectors": [],
        "policy": None,
        "provider": "unknown",
    }
