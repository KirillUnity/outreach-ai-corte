"""SPF checker — mocked DNS, no network."""

from unittest.mock import AsyncMock

import pytest

from app.services.deliverability.spf_checker import SPFChecker


def _checker(txts: list[str]) -> SPFChecker:
    resolver = AsyncMock()
    resolver.resolve_txt = AsyncMock(return_value=txts)
    return SPFChecker(resolver)


@pytest.mark.asyncio
async def test_spf_valid_hardfail() -> None:
    result = await _checker(["v=spf1 include:_spf.google.com -all"]).check("example.com")
    assert result["valid"] is True
    assert result["policy"] == "hardfail"
    assert result["record"] == "v=spf1 include:_spf.google.com -all"


@pytest.mark.asyncio
async def test_spf_valid_softfail() -> None:
    result = await _checker(["v=spf1 ~all"]).check("example.com")
    assert result["valid"] is True
    assert result["policy"] == "softfail"


@pytest.mark.asyncio
async def test_spf_no_record() -> None:
    result = await _checker([]).check("example.com")
    assert result["valid"] is False
    assert result["reason"] == "No SPF record found"


@pytest.mark.asyncio
async def test_spf_multiple_records() -> None:
    result = await _checker(["v=spf1 -all", "v=spf1 include:other.example ~all"]).check("example.com")
    assert result["valid"] is False
    assert result["reason"] == "Multiple SPF records"


@pytest.mark.asyncio
async def test_spf_lookup_limit_warning() -> None:
    includes = " ".join(f"include:_spf{i}.example.net" for i in range(11))
    result = await _checker([f"v=spf1 {includes} -all"]).check("example.com")
    assert result["valid"] is True
    assert result["lookup_count"] == 11
    assert any("lookup limit" in warning.lower() for warning in result["warnings"])
