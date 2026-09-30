"""DeliverabilityChecker orchestration with a fake DNSResolver."""

from unittest.mock import AsyncMock

import pytest

from app.core.config import DeliverabilitySettings, Settings
from app.services.deliverability.checker import DeliverabilityChecker, clear_deliverability_cache


def _settings() -> Settings:
    return Settings(deliverability=DeliverabilitySettings(cache_ttl_seconds=3600, dkim_selectors=["google"]))


def _resolver(
    *,
    spf: list[str],
    dkim: list[str],
    dmarc: list[str],
    mx: list[dict],
) -> AsyncMock:
    async def resolve_txt(name: str) -> list[str]:
        if name.startswith("_dmarc."):
            return dmarc
        if "._domainkey." in name:
            return dkim
        return spf

    async def resolve_mx(_domain: str) -> list[dict]:
        return mx

    resolver = AsyncMock()
    resolver.resolve_txt = AsyncMock(side_effect=resolve_txt)
    resolver.resolve_mx = AsyncMock(side_effect=resolve_mx)
    return resolver


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    clear_deliverability_cache()
    yield
    clear_deliverability_cache()


@pytest.mark.asyncio
async def test_check_domain_full_valid() -> None:
    resolver = _resolver(
        spf=["v=spf1 include:_spf.google.com -all"],
        dkim=["v=DKIM1; k=rsa; p=AAAA"],
        dmarc=["v=DMARC1; p=reject; rua=mailto:post@example.com"],
        mx=[{"priority": 1, "exchange": "aspmx.l.google.com"}],
    )
    checker = DeliverabilityChecker(settings=_settings(), resolver=resolver)
    result = await checker.check_domain("example.com")
    assert result["overall_score"] == 100
    assert result["risk_level"] == "low"
    assert result["spf"]["valid"] is True
    assert result["dkim"]["valid"] is True
    assert result["dmarc"]["valid"] is True
    assert result["mx"]["valid"] is True
    assert result["mx"]["provider"] == "google"


@pytest.mark.asyncio
async def test_check_domain_no_records() -> None:
    resolver = _resolver(spf=[], dkim=[], dmarc=[], mx=[])
    checker = DeliverabilityChecker(settings=_settings(), resolver=resolver)
    result = await checker.check_domain("missing.example")
    assert result["overall_score"] == 0
    assert result["risk_level"] == "critical"
    assert result["spf"]["valid"] is False
    assert result["dkim"]["valid"] is False
    assert result["dmarc"]["valid"] is False
    assert result["mx"]["valid"] is False


@pytest.mark.asyncio
async def test_check_domain_cache_hit() -> None:
    resolver = _resolver(
        spf=["v=spf1 -all"],
        dkim=["v=DKIM1; k=rsa; p=AAAA"],
        dmarc=["v=DMARC1; p=quarantine"],
        mx=[{"priority": 10, "exchange": "mail.example.com"}],
    )
    checker = DeliverabilityChecker(settings=_settings(), resolver=resolver)
    await checker.check_domain("cached.example")
    txt_after_first = resolver.resolve_txt.await_count
    mx_after_first = resolver.resolve_mx.await_count
    assert txt_after_first > 0
    await checker.check_domain("cached.example")
    assert resolver.resolve_txt.await_count == txt_after_first
    assert resolver.resolve_mx.await_count == mx_after_first


@pytest.mark.asyncio
async def test_recommendations_generated_for_missing_dmarc() -> None:
    resolver = _resolver(
        spf=["v=spf1 -all"],
        dkim=["v=DKIM1; k=rsa; p=AAAA"],
        dmarc=[],
        mx=[{"priority": 10, "exchange": "mail.example.com"}],
    )
    checker = DeliverabilityChecker(settings=_settings(), resolver=resolver)
    result = await checker.check_domain("nodmarc.example")
    assert any("DMARC" in item for item in result["recommendations"])
    assert result["dmarc"]["valid"] is False
    assert result["overall_score"] == 70
