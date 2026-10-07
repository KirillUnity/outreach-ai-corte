"""CRM adapters: mock (no network) and Bitrix httpx mapping."""

from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.core.config import CrmSettings, Settings
from app.models.crm_sync_event import CrmSyncEvent
from app.services.crm import CrmService
from app.services.crm.bitrix24_client import Bitrix24Client
from app.services.crm.mock_client import MockCrmClient


class _Db:
    def __init__(self, person: SimpleNamespace) -> None:
        self.person = person
        self.events: list[CrmSyncEvent] = []

    def add(self, row: CrmSyncEvent) -> None:
        self.events.append(row)

    async def execute(self, _stmt):  # type: ignore[no-untyped-def]
        outer = self

        class _Result:
            def scalar_one_or_none(self):  # type: ignore[no-untyped-def]
                return outer.person

            def scalars(self):  # type: ignore[no-untyped-def]
                return self

            def all(self):  # type: ignore[no-untyped-def]
                return list(outer.events)

        return _Result()

    async def commit(self) -> None:
        return None

    async def refresh(self, _row: CrmSyncEvent) -> None:
        return None


def _person() -> SimpleNamespace:
    company = SimpleNamespace(id=uuid4(), name="Stripe", domain="stripe.com")
    return SimpleNamespace(
        id=uuid4(),
        first_name="Ada",
        last_name="Lovelace",
        email="ada@stripe.com",
        title="Engineer",
        company=company,
        company_id=company.id,
    )


@pytest.mark.asyncio
async def test_mock_sync_creates_event() -> None:
    person = _person()
    db = _Db(person)
    settings = Settings(crm=CrmSettings(provider="mock", enabled=True))
    event = await CrmService(db, settings).sync_person(person.id)  # type: ignore[arg-type]
    assert event.status == "ok"
    assert event.provider == "mock"
    assert event.remote_id == f"mock-{person.id}"
    assert len(db.events) == 1


@pytest.mark.asyncio
async def test_bitrix_without_url_uses_mock() -> None:
    person = _person()
    db = _Db(person)
    settings = Settings(crm=CrmSettings(provider="bitrix24", webhook_url="", enabled=True))
    client = CrmService(db, settings).build_client()
    assert isinstance(client, MockCrmClient)


@pytest.mark.asyncio
async def test_bitrix_401_is_error_not_exception() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid"})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    person = _person()
    company = person.company
    client = Bitrix24Client("https://example.bitrix24.ru/rest/1/secret/", client=http)
    result = await client.upsert_lead(person, company, {})  # type: ignore[arg-type]
    await http.aclose()
    assert result["status"] == "error"
    assert result["raw"]["error"] == "http_401"


@pytest.mark.asyncio
async def test_bitrix_timeout_payload() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    person = _person()
    client = Bitrix24Client("https://example.bitrix24.ru/rest/1/secret/", client=http)
    result = await client.upsert_lead(person, person.company, {})  # type: ignore[arg-type]
    await http.aclose()
    assert result["status"] == "error"
    assert result["raw"]["error"] == "timeout"
