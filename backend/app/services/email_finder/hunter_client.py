"""Hunter.io email-finder HTTP client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class HunterClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        cfg = settings.email_finder
        self.enabled = bool(cfg.hunter_enabled and cfg.hunter_api_key)
        self._client = client

    async def find_email(self, first_name: str, last_name: str, domain: str) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        params = {
            "domain": domain,
            "first_name": first_name,
            "last_name": last_name,
            "api_key": self.settings.email_finder.hunter_api_key,
        }
        payload = await self._get("/email-finder", params)
        if payload is None:
            return []
        data = payload.get("data") or {}
        email = data.get("email")
        if not email:
            return []
        score = float(data.get("score") or 0) / 100.0
        return [
            {
                "email": str(email).strip().lower(),
                "confidence": min(0.9, max(0.0, score)),
                "source": "hunter",
                "raw": data,
            }
        ]

    async def verify_email(self, email: str) -> dict[str, Any]:
        if not self.enabled:
            return {"status": "unknown", "score": 0, "smtp_check": False}
        payload = await self._get("/email-verifier", {"email": email, "api_key": self.settings.email_finder.hunter_api_key})
        if payload is None:
            return {"status": "unknown", "score": 0, "smtp_check": False}
        data = payload.get("data") or {}
        return {
            "status": data.get("status"),
            "score": data.get("score"),
            "smtp_check": data.get("smtp_check"),
        }

    async def domain_search(self, domain: str, limit: int = 10) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        payload = await self._get(
            "/domain-search",
            {
                "domain": domain,
                "limit": limit,
                "api_key": self.settings.email_finder.hunter_api_key,
            },
        )
        if payload is None:
            return []
        emails = (payload.get("data") or {}).get("emails") or []
        return list(emails) if isinstance(emails, list) else []

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any] | None:
        url = f"{self.settings.email_finder.hunter_base_url.rstrip('/')}{path}"
        client = self._client
        owns = client is None
        if owns:
            client = httpx.AsyncClient(timeout=30.0)
        assert client is not None
        try:
            response = await client.get(url, params=params)
            if response.status_code == 401:
                logger.warning("hunter 401 invalid api key")
                return None
            if response.status_code == 429:
                logger.warning("hunter 429 rate limit")
                return None
            response.raise_for_status()
            body = response.json()
            return body if isinstance(body, dict) else None
        except httpx.TimeoutException:
            logger.warning("hunter timeout path=%s", path)
            return None
        except httpx.HTTPError:
            logger.warning("hunter http error path=%s", path, exc_info=True)
            return None
        finally:
            if owns:
                await client.aclose()
