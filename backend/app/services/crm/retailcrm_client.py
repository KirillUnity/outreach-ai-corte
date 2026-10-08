"""retailCRM customers/create. Empty key → caller should use mock."""

from __future__ import annotations

from typing import Any

import httpx

from app.models.company import Company
from app.models.person import Person


class RetailCrmClient:
    provider_name = "retailcrm"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client = client

    async def upsert_lead(
        self,
        person: Person,
        company: Company | None,
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        customer = {
            "firstName": person.first_name,
            "lastName": person.last_name,
            "email": person.email,
            "customFields": {"title": person.title} if person.title else {},
        }
        if company is not None:
            existing = customer.get("customFields") or {}
            customer["customFields"] = {**existing, "company": company.name}
        request = {"customer": customer}
        url = f"{self.base_url}/api/v5/customers/create"
        raw, err = await self._post(url, request)
        if err:
            return {"status": "error", "remote_id": None, "request": request, "raw": {"error": err}}
        ident = None
        if isinstance(raw, dict):
            ident = raw.get("id") or (raw.get("customer") or {}).get("id")
        return {
            "status": "ok" if ident is not None else "error",
            "remote_id": str(ident) if ident is not None else None,
            "request": request,
            "raw": raw,
        }

    async def _post(self, url: str, body: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
        client = self._client
        owns = client is None
        if owns:
            client = httpx.AsyncClient(timeout=self.timeout)
        assert client is not None
        try:
            response = await client.post(url, params={"apiKey": self.api_key}, json=body)
            if response.status_code in {401, 403}:
                return {}, f"http_{response.status_code}"
            response.raise_for_status()
            parsed = response.json()
            return (parsed if isinstance(parsed, dict) else {"body": parsed}), None
        except httpx.TimeoutException:
            return {}, "timeout"
        except httpx.HTTPError as exc:
            return {}, f"http_error:{exc.__class__.__name__}"
        finally:
            if owns:
                await client.aclose()
