"""DKIM checker — mocked TXT at selector._domainkey."""

from unittest.mock import AsyncMock

import pytest

from app.services.deliverability.dkim_checker import DKIMChecker


def _checker(mapping: dict[str, list[str]]) -> DKIMChecker:
    async def resolve_txt(name: str) -> list[str]:
        return mapping.get(name, [])

    resolver = AsyncMock()
    resolver.resolve_txt = AsyncMock(side_effect=resolve_txt)
    return DKIMChecker(resolver, ["google", "default"])


@pytest.mark.asyncio
async def test_dkim_finds_google_selector() -> None:
    record = "v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA"
    checker = _checker({"google._domainkey.example.com": [record]})
    result = await checker.check("example.com")
    assert result["valid"] is True
    assert result["selector"] == "google"
    assert result["key_type"] == "rsa"


@pytest.mark.asyncio
async def test_dkim_no_record() -> None:
    result = await _checker({}).check("example.com")
    assert result["valid"] is False
    assert "common selectors" in (result["reason"] or "")
    assert result["tried_selectors"] == ["google", "default"]


@pytest.mark.asyncio
async def test_dkim_revoked_key() -> None:
    checker = _checker({"google._domainkey.example.com": ["v=DKIM1; k=rsa; p="]})
    result = await checker.check("example.com")
    assert result["valid"] is False
    assert "revoked" in (result["reason"] or "").lower()
