"""Live API checks for company research + RAG (needs api + chroma up)."""

from collections.abc import Iterator
from uuid import uuid4

import httpx
import pytest


@pytest.fixture
def api_client() -> Iterator[httpx.Client]:
    with httpx.Client(base_url="http://127.0.0.1:8080", timeout=60.0) as client:
        yield client


def test_research_indexes_and_context_search(api_client: httpx.Client) -> None:
    domain = f"example-{uuid4().hex[:8]}.com"
    created = api_client.post(
        "/api/v1/companies/",
        json={"domain": domain, "name": "Example Co"},
    )
    assert created.status_code == 201, created.text

    # Seed site text so indexing does not depend on a live crawl of a random domain.
    patched = api_client.patch(
        f"/api/v1/companies/{domain}",
        json={
            "raw_site_text": (
                "Example Co sells invoicing software to finance teams. "
                "Pricing starts at forty nine dollars per month. "
                "Enterprise plans include SSO and audit logs. "
                "The product helps controllers close the books faster."
            )
            * 4
        },
    )
    assert patched.status_code == 200, patched.text

    # Fake TLD will not parse; existing raw_site_text is kept and indexed.
    research = api_client.post(f"/api/v1/companies/{domain}/research")
    assert research.status_code == 200, research.text
    body = research.json()
    assert body["chunks_indexed"] >= 1

    context = api_client.get(
        f"/api/v1/companies/{domain}/context",
        params={"q": "pricing for finance teams", "top_k": 3},
    )
    assert context.status_code == 200, context.text
    payload = context.json()
    assert payload["domain"] == domain
    assert payload["query"] == "pricing for finance teams"
    assert isinstance(payload["chunks"], list)
