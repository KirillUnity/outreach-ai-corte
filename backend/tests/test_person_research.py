"""Integration tests for POST /persons/research against the running API container."""

from collections.abc import Iterator
from uuid import uuid4

import httpx
import pytest


@pytest.fixture
def api_client() -> Iterator[httpx.Client]:
    """HTTP to uvicorn in this container (sync client — no event-loop teardown races)."""
    with httpx.Client(base_url="http://127.0.0.1:8080", timeout=30.0) as client:
        yield client


def _url(slug: str) -> str:
    return f"https://linkedin.com/in/{slug}"


def test_research_creates_person_and_company(api_client: httpx.Client) -> None:
    slug = f"day5-{uuid4().hex[:10]}"
    response = api_client.post("/api/v1/persons/research", json={"linkedin_url": _url(slug)})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "mock"
    assert body["person"]["linkedin_url"].endswith(slug)
    assert body["person"]["first_name"]
    assert body["person"]["raw_linkedin_data"]["current_title"]
    assert body["company"] is not None
    assert body["company"]["domain"].endswith(".com")


def test_research_returns_cache_on_second_call(api_client: httpx.Client) -> None:
    slug = f"day5-cache-{uuid4().hex[:10]}"
    first = api_client.post("/api/v1/persons/research", json={"linkedin_url": _url(slug)})
    assert first.status_code == 200, first.text
    first_body = first.json()
    second = api_client.post("/api/v1/persons/research", json={"linkedin_url": _url(slug)})
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["source"] == "cache"
    assert second_body["person"]["id"] == first_body["person"]["id"]


def test_research_with_existing_company(api_client: httpx.Client) -> None:
    domain = f"day5-{uuid4().hex[:8]}.com"
    created = api_client.post(
        "/api/v1/companies/",
        json={"domain": domain, "name": "Day5 Corp"},
    )
    assert created.status_code == 201, created.text
    slug = f"day5-bind-{uuid4().hex[:10]}"
    response = api_client.post(
        "/api/v1/persons/research",
        json={"linkedin_url": _url(slug), "company_domain": domain},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["company"]["domain"] == domain
    assert body["company"]["name"] == "Day5 Corp"
    assert body["person"]["company_id"] == body["company"]["id"]


def test_research_invalid_url_422(api_client: httpx.Client) -> None:
    response = api_client.post(
        "/api/v1/persons/research",
        json={"linkedin_url": "https://example.com/not-linkedin"},
    )
    assert response.status_code == 422
