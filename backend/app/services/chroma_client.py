"""Shared ChromaDB HTTP client (one instance per process)."""

from __future__ import annotations

import logging
from functools import lru_cache

import chromadb
from chromadb import HttpClient

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_chroma_client() -> HttpClient:
    """Return a process-wide HttpClient. Failed connects are not cached (raise)."""
    host = settings.rag.chroma_host
    port = settings.rag.chroma_port
    try:
        client = chromadb.HttpClient(host=host, port=port)
        client.heartbeat()
    except Exception as exc:
        raise ConnectionError(f"ChromaDB unreachable at {host}:{port}: {exc}") from exc
    logger.info("chroma client ready host=%s port=%s", host, port)
    return client


def reset_chroma_client() -> None:
    """Drop the cached client (after a failed health check or in tests)."""
    get_chroma_client.cache_clear()
