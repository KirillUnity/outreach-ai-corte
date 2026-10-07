"""Unit tests for LinkedInService — no network, no database."""

import pytest

from app.core.config import LinkedInSettings, Settings
from app.services.linkedin_service import LinkedInService


def _svc(delay: float = 0.01) -> LinkedInService:
    return LinkedInService(Settings(linkedin=LinkedInSettings(mode="mock", mock_delay_seconds=delay)))


async def test_mock_profile_deterministic() -> None:
    svc = _svc()
    url = "https://linkedin.com/in/johndoe"
    first = await svc._get_profile_mock(url, "johndoe")
    second = await svc._get_profile_mock(url, "johndoe")
    assert first.model_dump() == second.model_dump()
    assert first.source == "mock"


async def test_mock_profile_different_urls() -> None:
    svc = _svc()
    alice = await svc._get_profile_mock("https://linkedin.com/in/alice", "alice")
    bob = await svc._get_profile_mock("https://linkedin.com/in/bob", "bob")
    assert alice.model_dump() != bob.model_dump()


async def test_invalid_url_raises() -> None:
    svc = _svc()
    with pytest.raises(ValueError):
        await svc.get_profile("https://example.com/not-linkedin")
    with pytest.raises(ValueError):
        LinkedInService.extract_username("https://example.com/not-linkedin")


def test_extract_username_from_url() -> None:
    assert LinkedInService.extract_username("https://linkedin.com/in/johndoe") == "johndoe"
    assert LinkedInService.extract_username("https://www.linkedin.com/in/johndoe/") == "johndoe"
    assert LinkedInService.extract_username("http://linkedin.com/in/john-doe?trk=x") == "john-doe"


async def test_mock_delay_called(monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        delays.append(seconds)

    monkeypatch.setattr("app.services.linkedin_service.asyncio.sleep", fake_sleep)
    svc = _svc(delay=0.4)
    await svc._get_profile_mock("https://linkedin.com/in/johndoe", "johndoe")
    assert delays == [0.4]


async def test_people_search_deterministic() -> None:
    svc = _svc()
    first = await svc.search_people("stripe.com", title_contains="VP", limit=3)
    second = await svc.search_people("stripe.com", title_contains="VP", limit=3)
    assert len(first) == 3
    assert [p.linkedin_url for p in first] == [p.linkedin_url for p in second]
    assert all(p.source == "mock" for p in first)
    assert all(p.current_title == "VP" for p in first)


async def test_people_search_different_domains_differ() -> None:
    svc = _svc()
    a = await svc.search_people("acme.com", limit=1)
    b = await svc.search_people("other.com", limit=1)
    assert a[0].linkedin_url != b[0].linkedin_url


async def test_people_search_real_empty_key_falls_back_to_mock() -> None:
    svc = LinkedInService(
        Settings(
            linkedin=LinkedInSettings(
                mode="real",
                phantombuster_api_key="",
                people_search_phantom_id="search-1",
                mock_delay_seconds=0.01,
            )
        )
    )
    rows = await svc.search_people("stripe.com", limit=2)
    assert len(rows) == 2
    assert rows[0].source == "mock"


async def test_real_mode_requires_api_key() -> None:
    svc = LinkedInService(
        Settings(
            linkedin=LinkedInSettings(
                mode="real",
                phantombuster_api_key="",
                phantombuster_phantom_id="agent-1",
            )
        )
    )
    # Empty key → ValueError inside real path → fallback to mock (logged).
    profile = await svc.get_profile("https://linkedin.com/in/johndoe")
    assert profile.source == "mock"
