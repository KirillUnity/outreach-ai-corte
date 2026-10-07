"""CRM adapter contract."""

from __future__ import annotations

from typing import Any, Protocol

from app.models.company import Company
from app.models.person import Person


class CrmClient(Protocol):
    provider_name: str

    async def upsert_lead(
        self,
        person: Person,
        company: Company | None,
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        """Return {status: ok|error, remote_id, raw, request}."""
        ...
