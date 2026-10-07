"""Pick a CRM adapter from settings. Missing vendor creds → mock."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.models.crm_sync_event import CrmSyncEvent
from app.models.person import Person
from app.services.crm.bitrix24_client import Bitrix24Client
from app.services.crm.mock_client import MockCrmClient
from app.services.crm.retailcrm_client import RetailCrmClient
from app.services.exceptions import NotFoundError


class CrmService:
    def __init__(self, db: AsyncSession, settings: Settings, client: Any | None = None) -> None:
        self.db = db
        self.settings = settings
        self._client = client

    def build_client(self) -> Any:
        if self._client is not None:
            return self._client
        cfg = self.settings.crm
        if not cfg.enabled or cfg.provider == "mock":
            return MockCrmClient()
        if cfg.provider == "bitrix24":
            if not cfg.webhook_url:
                return MockCrmClient()
            return Bitrix24Client(cfg.webhook_url, timeout=cfg.timeout_seconds)
        if cfg.provider == "retailcrm":
            if not (cfg.api_key and cfg.base_url):
                return MockCrmClient()
            return RetailCrmClient(cfg.base_url, cfg.api_key, timeout=cfg.timeout_seconds)
        return MockCrmClient()

    async def sync_person(self, person_id, extra: dict[str, Any] | None = None) -> CrmSyncEvent:
        person = (
            await self.db.execute(
                select(Person).options(selectinload(Person.company)).where(Person.id == person_id)
            )
        ).scalar_one_or_none()
        if person is None:
            raise NotFoundError(f"Person '{person_id}' not found")
        client = self.build_client()
        extra = dict(extra or {})
        result = await client.upsert_lead(person, person.company, extra)
        now = datetime.now(timezone.utc)
        event = CrmSyncEvent(
            person_id=person.id,
            provider=getattr(client, "provider_name", self.settings.crm.provider),
            status=str(result.get("status") or "error"),
            remote_id=result.get("remote_id"),
            request_payload=result.get("request") if isinstance(result.get("request"), dict) else None,
            response_payload=result.get("raw") if isinstance(result.get("raw"), dict) else {"raw": result.get("raw")},
            created_at=now,
            updated_at=now,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def list_events(self, person_id=None, limit: int = 50, offset: int = 0) -> list[CrmSyncEvent]:
        stmt = select(CrmSyncEvent).order_by(CrmSyncEvent.created_at.desc()).limit(limit).offset(offset)
        if person_id is not None:
            stmt = stmt.where(CrmSyncEvent.person_id == person_id)
        return list((await self.db.execute(stmt)).scalars().all())
