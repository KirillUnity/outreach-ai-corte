"""Split company site text into overlapping LangChain Documents."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

logger = logging.getLogger(__name__)


class CompanyTextSplitter:
    """Recursive splitter tuned for scraped marketing pages (not code)."""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        min_chunk_chars: int | None = None,
        max_source_chars: int | None = None,
    ) -> None:
        rag = settings.rag
        self.chunk_size = chunk_size if chunk_size is not None else rag.chunk_size
        self.chunk_overlap = chunk_overlap if chunk_overlap is not None else rag.chunk_overlap
        self.min_chunk_chars = (
            min_chunk_chars if min_chunk_chars is not None else rag.min_chunk_chars
        )
        self.max_source_chars = (
            max_source_chars if max_source_chars is not None else rag.max_source_chars
        )
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
            length_function=len,
        )

    def split(self, text: str, metadata: dict[str, Any] | None = None) -> list[Document]:
        """Return Documents with per-chunk metadata. Empty / tiny chunks are dropped."""
        base_meta = dict(metadata or {})
        source = (text or "").strip()
        if len(source) > self.max_source_chars:
            logger.warning(
                "truncating source from %s to %s chars domain=%s",
                len(source),
                self.max_source_chars,
                base_meta.get("company_domain"),
            )
            source = source[: self.max_source_chars]

        if not source:
            return []

        raw_chunks = self._splitter.split_text(source)
        kept = [chunk.strip() for chunk in raw_chunks if len(chunk.strip()) >= self.min_chunk_chars]
        total = len(kept)
        documents: list[Document] = []
        for index, chunk in enumerate(kept):
            documents.append(
                Document(
                    page_content=chunk,
                    metadata={
                        **base_meta,
                        "chunk_index": index,
                        "total_chunks": total,
                    },
                )
            )
        logger.info(
            "split domain=%s raw=%s kept=%s",
            base_meta.get("company_domain"),
            len(raw_chunks),
            total,
        )
        return documents
