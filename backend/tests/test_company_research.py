"""Company research + RAG wiring — no live Chroma, no live HTTP."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.company_service import CompanyService
from app.services.site_parser import ParseResult


class _FakeResult:
    def scalar_one_or_none(self):
        return self.value

    def __init__(self, value):
        self.value = value


class _FakeSession:
    def __init__(self, company):
        self._company = company
        self.committed = False

    async def execute(self, _stmt):
        return _FakeResult(self._company)

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, _obj) -> None:
        return None


class _FakeParser:
    def __init__(self, parsed: ParseResult) -> None:
        self.parsed = parsed

    async def parse_company_site(self, domain: str) -> ParseResult:
        assert domain == self.parsed.domain
        return self.parsed


class _FakeRag:
    def __init__(self, chunks: int = 3, fail: bool = False) -> None:
        self.chunks = chunks
        self.fail = fail
        self.calls: list[dict] = []

    async def index_company(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("chroma down")
        return self.chunks


@pytest.mark.asyncio
async def test_research_indexes_chunks() -> None:
    company = SimpleNamespace(
        id=uuid4(),
        domain="acme.test",
        name="Acme",
        description=None,
        raw_site_text=None,
    )
    parsed = ParseResult(
        domain="acme.test",
        title="Acme",
        description="Widgets",
        raw_text="Acme builds widgets for teams. " * 20,
        pages_parsed=2,
        errors=[],
    )
    rag = _FakeRag(chunks=4)
    service = CompanyService(_FakeSession(company), parser=_FakeParser(parsed), rag=rag)

    out_company, out_parsed, chunks = await service.research("acme.test")
    assert chunks == 4
    assert out_company.raw_site_text == parsed.raw_text
    assert out_company.description == "Widgets"
    assert rag.calls[0]["domain"] == "acme.test"
    assert out_parsed.errors == []


@pytest.mark.asyncio
async def test_research_keeps_existing_text_when_parse_empty() -> None:
    company = SimpleNamespace(
        id=uuid4(),
        domain="acme.test",
        name="Acme",
        description="Existing",
        raw_site_text="Previously saved site text that is long enough to index.",
    )
    parsed = ParseResult(
        domain="acme.test",
        title="",
        description="",
        raw_text="",
        pages_parsed=0,
        errors=["failed to fetch https://acme.test"],
    )
    rag = _FakeRag(chunks=1)
    service = CompanyService(_FakeSession(company), parser=_FakeParser(parsed), rag=rag)

    _company, out_parsed, chunks = await service.research("acme.test")
    assert company.raw_site_text.startswith("Previously saved")
    assert chunks == 1
    assert out_parsed.errors


@pytest.mark.asyncio
async def test_research_survives_rag_failure() -> None:
    company = SimpleNamespace(
        id=uuid4(),
        domain="acme.test",
        name="Acme",
        description="Existing",
        raw_site_text=None,
    )
    parsed = ParseResult(
        domain="acme.test",
        title="Acme",
        description="Widgets",
        raw_text="enough text to index",
        pages_parsed=1,
        errors=[],
    )
    rag = _FakeRag(fail=True)
    service = CompanyService(_FakeSession(company), parser=_FakeParser(parsed), rag=rag)

    _company, out_parsed, chunks = await service.research("acme.test")
    assert chunks == 0
    assert any("RAG index failed" in err for err in out_parsed.errors)
    assert company.raw_site_text == "enough text to index"
