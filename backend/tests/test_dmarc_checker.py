"""DMARC checker — mocked _dmarc TXT."""

from unittest.mock import AsyncMock

import pytest

from app.services.deliverability.dmarc_checker import DMARCChecker


def _checker(txts: list[str]) -> DMARCChecker:
    resolver = AsyncMock()
    resolver.resolve_txt = AsyncMock(return_value=txts)
    return DMARCChecker(resolver)


@pytest.mark.asyncio
async def test_dmarc_reject_policy() -> None:
    record = "v=DMARC1; p=reject; rua=mailto:dmarc@example.com; pct=100"
    result = await _checker([record]).check("example.com")
    assert result["valid"] is True
    assert result["policy"] == "reject"
    assert result["pct"] == 100
    assert result["rua"] == ["mailto:dmarc@example.com"]


@pytest.mark.asyncio
async def test_dmarc_none_policy_warning() -> None:
    record = "v=DMARC1; p=none"
    result = await _checker([record]).check("example.com")
    assert result["valid"] is True
    assert result["policy"] == "none"
    assert any("p=none" in warning for warning in result["warnings"])
    assert any("rua" in warning.lower() for warning in result["warnings"])


@pytest.mark.asyncio
async def test_dmarc_no_record() -> None:
    result = await _checker([]).check("example.com")
    assert result["valid"] is False
    assert result["reason"] == "No DMARC record"
