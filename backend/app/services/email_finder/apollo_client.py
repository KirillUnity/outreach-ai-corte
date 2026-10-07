"""Apollo.io people/org lookup. Disabled unless API key is set — no network then."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class ApolloClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        cfg = settings.email_finder
        self.enabled = bool(cfg.apollo_enabled and cfg.apollo_api_key)
        self._client = client

    async def match_person(self, first_name: str, last_name: str, domain: str) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        payload = await self._post(
            "/people/match",
            {
                "first_name": first_name,
                "last_name": last_name,
                "organization_domain": domain,
            },
        )
        if payload is None:
            return []
        person = payload.get("person") or payload.get("data") or payload
        if not isinstance(person, dict):
            return []
        email = person.get("email") or person.get("email_status")
        if not email or not isinstance(email, str) or "@" not in email:
            return []
        score = float(person.get("email_confidence") or person.get("score") or 70)
        if score > 1:
            score = score / 100.0
        return [
            {
                "email": email.strip().lower(),
                "confidence": min(0.85, max(0.0, score)),
                "source": "apollo",
                "raw": person,
            }
        ]

    async def org_search(self, domain: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        payload = await self._post("/organizations/enrich", {"domain": domain})
        if payload is None:
            return None
        org = payload.get("organization") or payload.get("data")
        return org if isinstance(org, dict) else payload

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any] | None:
        cfg = self.settings.email_finder
        url = f"{str(cfg.apollo_base_url).rstrip('/')}{path}"
        client = self._client
        owns = client is None
        if owns:
            client = httpx.AsyncClient(timeout=30.0)
        assert client is not None
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": str(cfg.apollo_api_key),
        }
        try:
            response = await client.post(url, json=body, headers=headers)
            if response.status_code in {401, 403}:
                logger.warning("apollo %s invalid api key", response.status_code)
                return None
            if response.status_code == 429:
                logger.warning("apollo 429 rate limit")
                return None
            response.raise_for_status()
            parsed = response.json()
            return parsed if isinstance(parsed, dict) else None
        except httpx.TimeoutException:
            logger.warning("apollo timeout path=%s", path)
            return None
        except httpx.HTTPError:
            logger.warning("apollo http error path=%s", path, exc_info=True)
            return None
        finally:
            if owns:
                await client.aclose()
