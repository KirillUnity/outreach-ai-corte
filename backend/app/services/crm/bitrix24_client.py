"""Bitrix24 inbound webhook contact add. Empty URL → caller should use mock."""

from __future__ import annotations

from typing import Any

import httpx

from app.models.company import Company
from app.models.person import Person


class Bitrix24Client:
    provider_name = "bitrix24"

    def __init__(
        self,
        webhook_url: str,
        timeout: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.webhook_url = webhook_url.rstrip("/") + "/"
        self.timeout = timeout
        self._client = client

    async def upsert_lead(
        self,
        person: Person,
        company: Company | None,
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        fields = {
            "NAME": person.first_name,
            "LAST_NAME": person.last_name,
            "EMAIL": [{"VALUE": person.email, "VALUE_TYPE": "WORK"}] if person.email else [],
            "POST": person.title or "",
            "COMMENTS": extra.get("comments") or "",
        }
        if company is not None:
            fields["COMPANY_TITLE"] = company.name
        request = {"fields": fields}
        url = f"{self.webhook_url}crm.contact.add.json"
        raw, err = await self._post(url, request)
        if err:
            return {"status": "error", "remote_id": None, "request": request, "raw": {"error": err}}
        result = raw.get("result") if isinstance(raw, dict) else None
        return {
            "status": "ok" if result is not None else "error",
            "remote_id": str(result) if result is not None else None,
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
            response = await client.post(url, json=body)
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
