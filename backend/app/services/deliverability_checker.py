"""Lightweight deliverability gate used by the outreach agent.

Looks up an existing DomainHealth snapshot. Does not run live DNS in Day 8 —
that belongs with a dedicated checker later. Missing snapshot is a hold when
`require_deliverability_check` is on.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.models.domain_health import DomainHealth
from app.services.domain_health_service import DomainHealthService

logger = logging.getLogger(__name__)

_DOMAIN_RE = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$",
    re.IGNORECASE,
)


def infer_sender_domain(sender_company: str, configured: str = "") -> str:
    """Prefer an explicit sending domain; else a hostname-like company name."""
    if configured.strip():
        return configured.strip().lower()
    candidate = sender_company.strip().lower().replace(" ", "")
    if _DOMAIN_RE.fullmatch(candidate):
        return candidate
    return candidate


class DeliverabilityChecker:
    """Read DomainHealth and decide if we should risk sending."""

    def __init__(self, domain_health: DomainHealthService | None = None) -> None:
        self._domain_health = domain_health

    async def check_domain(self, domain: str) -> dict[str, Any]:
        """Return `{ok, domain, reason, ...}`. `ok=False` when records are weak or missing."""
        normalized = (domain or "").strip().lower()
        if not normalized:
            return {"ok": False, "domain": domain, "reason": "empty sender domain"}

        row: DomainHealth | None = None
        if self._domain_health is not None:
            row = await self._domain_health.get_by_domain(normalized)

        if row is None:
            logger.info("deliverability no snapshot domain=%s", normalized)
            return {
                "ok": False,
                "domain": normalized,
                "reason": "no domain_health snapshot",
                "spf_valid": False,
                "dkim_valid": False,
            }

        ok = bool(row.spf_valid and row.dkim_valid)
        reason = "spf+dkim valid" if ok else "spf or dkim missing"
        return {
            "ok": ok,
            "domain": normalized,
            "reason": reason,
            "spf_valid": row.spf_valid,
            "dkim_valid": row.dkim_valid,
            "dmarc_policy": row.dmarc_policy,
        }
