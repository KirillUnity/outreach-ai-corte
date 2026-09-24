"""Unit tests for CompanyTextSplitter — no network, no Chroma."""

from app.services.text_splitter import CompanyTextSplitter


def test_split_assigns_metadata() -> None:
    splitter = CompanyTextSplitter(chunk_size=80, chunk_overlap=10, min_chunk_chars=20)
    text = (
        "Acme builds billing APIs for platforms.\n\n"
        "Our product helps finance teams reconcile payouts.\n\n"
        "Pricing starts at a simple monthly fee for startups."
    )
    docs = splitter.split(text, {"company_id": "abc", "company_domain": "acme.test"})
    assert docs
    assert docs[0].metadata["company_domain"] == "acme.test"
    assert docs[0].metadata["company_id"] == "abc"
    assert docs[0].metadata["chunk_index"] == 0
    assert docs[-1].metadata["total_chunks"] == len(docs)


def test_split_filters_tiny_chunks() -> None:
    splitter = CompanyTextSplitter(chunk_size=40, chunk_overlap=0, min_chunk_chars=50)
    docs = splitter.split("Too short.", {"company_domain": "x.test"})
    assert docs == []


def test_split_truncates_huge_source() -> None:
    splitter = CompanyTextSplitter(
        chunk_size=100,
        chunk_overlap=0,
        min_chunk_chars=10,
        max_source_chars=80,
    )
    docs = splitter.split("word " * 200, {"company_domain": "huge.test"})
    combined = "".join(doc.page_content for doc in docs)
    assert len(combined) <= 200


def test_split_empty_text() -> None:
    splitter = CompanyTextSplitter()
    assert splitter.split("   ") == []
