"""HunterClient HTTP error mapping (no live Hunter.io)."""

from types import SimpleNamespace

import httpx
import pytest

from app.services.email_finder.hunter_client import HunterClient


def _settings(*, enabled: bool, key: str = "test-key") -> SimpleNamespace:
    return SimpleNamespace(
        email_finder=SimpleNamespace(
            hunter_enabled=enabled,
            hunter_api_key=key,
            hunter_base_url="https://api.hunter.io/v2",
        )
    )


@pytest.mark.asyncio
async def test_disabled_when_no_key() -> None:
    client = HunterClient(_settings(enabled=True, key=""))
    assert client.enabled is False
    assert await client.find_email("Ada", "Lovelace", "acme.com") == []


@pytest.mark.asyncio
async def test_find_email_returns_candidates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/email-finder" in str(request.url)
        return httpx.Response(
            200,
            json={"data": {"email": "ada@acme.com", "score": 88, "sources": []}},
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = HunterClient(_settings(enabled=True), client=http)
    rows = await client.find_email("Ada", "Lovelace", "acme.com")
    await http.aclose()
    assert rows[0]["email"] == "ada@acme.com"
    assert rows[0]["confidence"] == pytest.approx(0.88)
    assert rows[0]["source"] == "hunter"


@pytest.mark.asyncio
async def test_handles_401_invalid_key() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"errors": [{"id": "invalid_api_key"}]})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = HunterClient(_settings(enabled=True), client=http)
    assert await client.find_email("Ada", "Lovelace", "acme.com") == []
    await http.aclose()


@pytest.mark.asyncio
async def test_handles_429_rate_limit() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"errors": [{"id": "rate_limit"}]})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = HunterClient(_settings(enabled=True), client=http)
    assert await client.find_email("Ada", "Lovelace", "acme.com") == []
    await http.aclose()
