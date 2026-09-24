"""Index company text in Chroma and run semantic search.

Real mode calls a cloud embedding API (OpenAI or OpenRouter). Mock mode
builds a deterministic hash vector — not a local neural net.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import re
from typing import Any, Protocol
from uuid import UUID

import tiktoken

from app.core.config import Settings, settings as default_settings
from app.services.chroma_client import get_chroma_client
from app.services.text_splitter import CompanyTextSplitter

logger = logging.getLogger(__name__)

_COLLECTION_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class HashEmbedder:
    """Deterministic unit vectors from sha256. For tests / RAG_MODE=mock only."""

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw = (digest * (self.dimensions // len(digest) + 1))[: self.dimensions]
        values = [(byte / 127.5) - 1.0 for byte in raw]
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]


class OpenAIEmbedder:
    """Cloud embeddings via langchain-openai (OpenAI or OpenRouter base_url)."""

    def __init__(self, settings: Settings) -> None:
        from langchain_openai import OpenAIEmbeddings

        rag = settings.rag
        if not rag.openai_api_key:
            raise ValueError("OPENAI_API_KEY is empty — cannot embed in RAG_MODE=real")
        kwargs: dict[str, Any] = {
            "model": rag.embedding_model,
            "api_key": rag.openai_api_key,
            "dimensions": rag.embedding_dimensions,
        }
        if rag.openai_base_url:
            kwargs["base_url"] = rag.openai_base_url
        self._client = OpenAIEmbeddings(**kwargs)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._client.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._client.embed_query(text)


class RAGService:
    """Split → embed → upsert into `company_{domain}`; query with the same embedder."""

    def __init__(
        self,
        settings: Settings | None = None,
        splitter: CompanyTextSplitter | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        self.settings = settings or default_settings
        self.splitter = splitter or CompanyTextSplitter(
            chunk_size=self.settings.rag.chunk_size,
            chunk_overlap=self.settings.rag.chunk_overlap,
            min_chunk_chars=self.settings.rag.min_chunk_chars,
            max_source_chars=self.settings.rag.max_source_chars,
        )
        self._embedder = embedder

    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            if self.settings.rag.mode == "real":
                self._embedder = OpenAIEmbedder(self.settings)
            else:
                self._embedder = HashEmbedder(self.settings.rag.embedding_dimensions)
        return self._embedder

    def collection_name(self, domain: str) -> str:
        safe = _COLLECTION_SAFE.sub("_", domain.strip().lower()).strip("._-")
        if len(safe) < 3:
            safe = f"{safe}co"
        return f"{self.settings.rag.collection_prefix}{safe}"[:63]

    async def index_company(
        self,
        *,
        company_id: UUID,
        domain: str,
        text: str,
    ) -> int:
        """Replace the company's collection with freshly split + embedded chunks."""
        return await asyncio.to_thread(self._index_company_sync, company_id, domain, text)

    async def search(self, domain: str, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        """Return top_k similar chunks for `query`."""
        return await asyncio.to_thread(self._search_sync, domain, query, top_k)

    def estimate_tokens(self, texts: list[str]) -> int:
        """tiktoken count for cost awareness (cl100k_base ≈ embedding-3)."""
        try:
            encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            return sum(len(text) // 4 for text in texts)
        return sum(len(encoder.encode(text)) for text in texts)

    def _index_company_sync(self, company_id: UUID, domain: str, text: str) -> int:
        documents = self.splitter.split(
            text,
            metadata={"company_id": str(company_id), "company_domain": domain},
        )
        if not documents:
            logger.info("rag skip empty split domain=%s", domain)
            return 0

        contents = [doc.page_content for doc in documents]
        tokens = self.estimate_tokens(contents)
        logger.info("rag embed domain=%s chunks=%s tokens≈%s", domain, len(contents), tokens)

        embeddings = self.embedder.embed_documents(contents)
        name = self.collection_name(domain)
        client = get_chroma_client()
        try:
            client.delete_collection(name)
        except Exception:
            logger.debug("chroma collection %s did not exist yet", name)

        collection = client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
        ids = [f"{domain}:{doc.metadata['chunk_index']}" for doc in documents]
        metadatas = [dict(doc.metadata) for doc in documents]
        # Chroma metadata values must be scalar.
        for meta in metadatas:
            for key, value in list(meta.items()):
                if value is None:
                    del meta[key]
                elif not isinstance(value, str | int | float | bool):
                    meta[key] = str(value)

        collection.add(ids=ids, documents=contents, embeddings=embeddings, metadatas=metadatas)
        logger.info("rag indexed domain=%s collection=%s chunks=%s", domain, name, len(ids))
        return len(ids)

    def _search_sync(self, domain: str, query: str, top_k: int | None) -> list[dict[str, Any]]:
        k = top_k if top_k is not None else self.settings.rag.top_k
        name = self.collection_name(domain)
        client = get_chroma_client()
        try:
            collection = client.get_collection(name)
        except Exception:
            return []
        query_embedding = self.embedder.embed_query(query)
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=max(1, k),
            include=["documents", "metadatas", "distances"],
        )
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        hits: list[dict[str, Any]] = []
        for text, meta, distance in zip(documents, metadatas, distances, strict=False):
            hits.append(
                {
                    "text": text,
                    "score": None if distance is None else round(1.0 / (1.0 + float(distance)), 4),
                    "distance": distance,
                    "chunk_index": (meta or {}).get("chunk_index"),
                    "metadata": meta or {},
                }
            )
        return hits
