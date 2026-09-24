"""RAG unit tests — hash embedder, no OpenAI, Chroma optional via monkeypatch."""

from uuid import uuid4

import pytest

from app.core.config import RAGSettings, Settings
from app.services.rag_service import HashEmbedder, RAGService


def test_hash_embedder_is_deterministic() -> None:
    embedder = HashEmbedder(dimensions=32)
    first = embedder.embed_query("pricing for startups")
    second = embedder.embed_query("pricing for startups")
    other = embedder.embed_query("careers at the company")
    assert first == second
    assert first != other
    assert len(first) == 32


def test_collection_name_is_safe() -> None:
    svc = RAGService(Settings(rag=RAGSettings(collection_prefix="company_")))
    assert svc.collection_name("Stripe.com") == "company_stripe.com"
    assert " " not in svc.collection_name("bad domain!!")


def test_estimate_tokens_positive() -> None:
    svc = RAGService()
    assert svc.estimate_tokens(["hello world"] * 3) > 0


class _FakeCollection:
    def __init__(self) -> None:
        self.ids: list[str] = []
        self.documents: list[str] = []
        self.embeddings: list[list[float]] = []
        self.metadatas: list[dict] = []

    def add(self, ids, documents, embeddings, metadatas) -> None:
        self.ids = list(ids)
        self.documents = list(documents)
        self.embeddings = list(embeddings)
        self.metadatas = list(metadatas)

    def query(self, query_embeddings, n_results, include):
        n = min(n_results, len(self.documents))
        return {
            "documents": [self.documents[:n]],
            "metadatas": [self.metadatas[:n]],
            "distances": [[0.1] * n],
        }


class _FakeChroma:
    def __init__(self) -> None:
        self.store: dict[str, _FakeCollection] = {}

    def delete_collection(self, name: str) -> None:
        self.store.pop(name, None)

    def get_or_create_collection(self, name: str, metadata=None) -> _FakeCollection:
        self.store[name] = _FakeCollection()
        return self.store[name]

    def get_collection(self, name: str) -> _FakeCollection:
        return self.store[name]


async def test_index_and_search_with_fake_chroma(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeChroma()
    monkeypatch.setattr("app.services.rag_service.get_chroma_client", lambda: fake)

    svc = RAGService(
        Settings(
            rag=RAGSettings(
                mode="mock",
                chunk_size=80,
                chunk_overlap=10,
                min_chunk_chars=20,
            )
        )
    )
    domain = "acme.test"
    text = (
        "Acme builds billing APIs for platforms.\n\n"
        "Our product helps finance teams reconcile payouts.\n\n"
        "Pricing starts at a simple monthly fee for startups."
    )
    count = await svc.index_company(company_id=uuid4(), domain=domain, text=text)
    assert count >= 1
    hits = await svc.search(domain, "pricing for startups", top_k=3)
    assert hits
    assert hits[0]["text"]
    assert hits[0]["score"] is not None
