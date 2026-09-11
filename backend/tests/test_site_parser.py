"""Unit tests for SiteParser — HTTP is mocked, never hit the network."""

import pytest

from app.core.config import ParserSettings, Settings
from app.services.site_parser import SiteParser


async def test_extract_text_from_html(settings: Settings, mock_html: str) -> None:
    parser = SiteParser(settings)
    text = await parser.extract_text(mock_html)
    assert "Acme builds reliable widgets" in text
    assert "Welcome to Acme" in text


async def test_extract_text_removes_scripts(settings: Settings, mock_html: str) -> None:
    parser = SiteParser(settings)
    text = await parser.extract_text(mock_html)
    assert "do-not-extract" not in text
    assert "SECRET" not in text


async def test_parse_company_site_mock(mock_html: str, monkeypatch: pytest.MonkeyPatch) -> None:
    parser = SiteParser(
        Settings(
            parser=ParserSettings(
                timeout=5,
                max_retries=0,
                max_text_length=5000,
                follow_links=["/about"],
            )
        )
    )

    async def fake_fetch(url: str) -> str | None:
        if url.rstrip("/").endswith("acme.test") or url.endswith("acme.test/"):
            return mock_html
        if url.endswith("/about"):
            return "<html><body><p>About Acme since 1999.</p></body></html>"
        return None

    monkeypatch.setattr(parser, "fetch_page", fake_fetch)

    result = await parser.parse_company_site("acme.test")
    assert result.domain == "acme.test"
    assert result.title == "Acme Widgets"
    assert result.description == "We sell widgets."
    assert result.pages_parsed == 2
    assert "reliable widgets" in result.raw_text
    assert "About Acme since 1999" in result.raw_text
    assert result.errors == []


async def test_parse_truncates_long_text(settings: Settings) -> None:
    parser = SiteParser(settings)
    long_body = "word " * 200
    html = f"<html><body><p>{long_body}</p></body></html>"
    text = await parser.extract_text(html)
    assert len(text) <= settings.parser.max_text_length


async def test_parse_company_site_homepage_down(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    parser = SiteParser(settings)

    async def fake_fetch(_url: str) -> str | None:
        return None

    monkeypatch.setattr(parser, "fetch_page", fake_fetch)
    result = await parser.parse_company_site("down.test")
    assert result.pages_parsed == 0
    assert result.raw_text == ""
    assert result.errors
    assert "failed to fetch https://down.test" in result.errors[0]


async def test_extract_uses_small_limit() -> None:
    tight = Settings(parser=ParserSettings(max_text_length=20, follow_links=[]))
    parser = SiteParser(tight)
    html = "<html><body><p>abcdefghijklmnopqrstuvwxyz</p></body></html>"
    text = await parser.extract_text(html)
    assert len(text) <= 20
