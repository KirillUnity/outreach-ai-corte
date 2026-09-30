"""Async DNS lookups via dnspython (TXT/MX/CNAME/A)."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings, settings as default_settings

logger = logging.getLogger(__name__)


class DNSResolver:
    """Thin wrapper around `dns.asyncresolver.Resolver` with safe empty fallbacks."""

    def __init__(self, settings: Settings | None = None) -> None:
        import dns.asyncresolver

        cfg = (settings or default_settings).deliverability
        self._resolver = dns.asyncresolver.Resolver()
        self._resolver.nameservers = list(cfg.dns_nameservers)
        self._resolver.timeout = cfg.dns_timeout
        self._resolver.lifetime = cfg.dns_lifetime

    async def resolve_txt(self, name: str) -> list[str]:
        """Return concatenated TXT strings (RFC 7208 character-strings joined)."""
        records = await self._resolve(name, "TXT")
        out: list[str] = []
        for rdata in records:
            out.append(_txt_join(rdata))
        return [item for item in out if item]

    async def resolve_mx(self, domain: str) -> list[dict[str, Any]]:
        records = await self._resolve(domain, "MX")
        rows: list[dict[str, Any]] = []
        for rdata in records:
            exchange = str(getattr(rdata, "exchange", "")).rstrip(".")
            rows.append(
                {
                    "priority": int(getattr(rdata, "preference", 0)),
                    "exchange": exchange,
                }
            )
        rows.sort(key=lambda item: item["priority"])
        return rows

    async def resolve_cname(self, name: str) -> str | None:
        records = await self._resolve(name, "CNAME")
        if not records:
            return None
        target = getattr(records[0], "target", None)
        if target is None:
            return None
        return str(target).rstrip(".")

    async def resolve_a(self, name: str) -> list[str]:
        records = await self._resolve(name, "A")
        return [str(getattr(rdata, "address", "")).strip() for rdata in records if getattr(rdata, "address", None)]

    async def _resolve(self, name: str, rdtype: str) -> list[Any]:
        import dns.exception
        import dns.resolver

        try:
            answer = await self._resolver.resolve(name, rdtype)
            return list(answer)
        except (
            dns.resolver.NXDOMAIN,
            dns.resolver.NoAnswer,
            dns.resolver.NoNameservers,
            dns.resolver.LifetimeTimeout,
            dns.exception.Timeout,
        ) as exc:
            logger.warning("dns %s %s failed: %s", rdtype, name, exc.__class__.__name__)
            return []
        except Exception:
            logger.warning("dns %s %s unexpected error", rdtype, name, exc_info=True)
            return []


def _txt_join(rdata: Any) -> str:
    strings = getattr(rdata, "strings", None)
    if strings:
        parts: list[str] = []
        for chunk in strings:
            if isinstance(chunk, bytes):
                parts.append(chunk.decode("utf-8", "replace"))
            else:
                parts.append(str(chunk))
        return "".join(parts)
    return str(rdata).strip().strip('"')
