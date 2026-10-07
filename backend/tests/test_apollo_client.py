"""ApolloClient HTTP mapping (no live Apollo)."""

from types import SimpleNamespace

import httpx
import pytest

from app.services.email_finder.apollo_client import ApolloClient


def _settings(*, enabled: bool, key: str = "test-key") -> SimpleNamespace:
    return SimpleNamespace(
        email_finder=SimpleNamespace(
            apollo_enabled=enabled,
            apollo_api_key=key,
            apollo_base_url="https://api.apollo.io/api/v1",
        )
    )


@pytest.mark.asyncio
async def test_apollo_disabled_no_http() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(500)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ApolloClient(_settings(enabled=True, key=""), client=http)
    assert client.enabled is False
    assert await client.match_person("Ada", "Lovelace", "acme.com") == []
    assert calls == []
    await http.aclose()


@pytest.mark.asyncio
async def test_apollo_match_returns_candidate() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/people/match" in str(request.url)
        return httpx.Response(
            200,
            json={"person": {"email": "ada@acme.com", "email_confidence": 80}},
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ApolloClient(_settings(enabled=True), client=http)
    rows = await client.match_person("Ada", "Lovelace", "acme.com")
    await http.aclose()
    assert rows[0]["email"] == "ada@acme.com"
    assert rows[0]["confidence"] == pytest.approx(0.80)
    assert rows[0]["source"] == "apollo"


@pytest.mark.asyncio
async def test_apollo_401() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid key"})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ApolloClient(_settings(enabled=True), client=http)
    assert await client.match_person("Ada", "Lovelace", "acme.com") == []
    await http.aclose()
