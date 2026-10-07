"""Local CRM stand-in: no HTTP."""

from __future__ import annotations

from typing import Any

from app.models.company import Company
from app.models.person import Person


class MockCrmClient:
    provider_name = "mock"

    async def upsert_lead(
        self,
        person: Person,
        company: Company | None,
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        remote = f"mock-{person.id}"
        request = {
            "first_name": person.first_name,
            "last_name": person.last_name,
            "email": person.email,
            "company": company.name if company is not None else None,
            "title": person.title,
            "extra_keys": sorted(extra.keys()),
        }
        return {
            "status": "ok",
            "remote_id": remote,
            "request": request,
            "raw": {"id": remote, "provider": "mock"},
        }
