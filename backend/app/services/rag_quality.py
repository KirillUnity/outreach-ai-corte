"""Compare hash-embedding retrieval with labeled teaching fragments.

The check uses ``HashEmbedder`` only. It does not call a cloud model,
Chroma, or ``RAG_MODE=real``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import NotRequired, TypedDict

from app.services.rag_service import HashEmbedder

# Same width as mock RAG embeddings. Ranking matches any multiple of the
# 32-byte sha256 digest; 1536 keeps the vectors the same shape as mock mode.
_HASH_DIMENSIONS = 1536


class Fragment(TypedDict):
    """One teaching chunk: stable id and the text that is embedded."""

    id: str
    text: str


class RetrievalQuestion(TypedDict):
    """Question plus the fragment that should win and the one that must not."""

    question: str
    expected_id: str
    rejected_id: str
    fragments: NotRequired[list[Fragment]]


@dataclass(frozen=True)
class Result:
    """Verdict for a single labeled question."""

    question: str
    expected_id: str
    rejected_id: str
    found_ids: tuple[str, ...]
    passed: bool
    error: str | None = None


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def search_fragments(question: str, fragments: Sequence[Fragment]) -> list[str]:
    """Return the fragment id nearest to ``question`` by hash cosine.

    Args:
        question: Query text embedded with ``HashEmbedder``.
        fragments: Candidate chunks. All of them are scored; none are dropped
            before ranking.

    Returns:
        The best fragment id, or an empty list when there is nothing to rank.
    """
    if not fragments:
        return []

    embedder = HashEmbedder(_HASH_DIMENSIONS)
    query_vector = embedder.embed_query(question)
    document_vectors = embedder.embed_documents([item["text"] for item in fragments])
    best_index = 0
    best_score = _cosine(query_vector, document_vectors[0])
    for index, document_vector in enumerate(document_vectors[1:], start=1):
        score = _cosine(query_vector, document_vector)
        if score > best_score:
            best_index = index
            best_score = score
    return [fragments[best_index]["id"]]


def _catalog(
    question: RetrievalQuestion,
    fragments: Sequence[Fragment] | None,
) -> list[Fragment]:
    own = question.get("fragments")
    if own:
        return list(own)
    if fragments:
        return list(fragments)
    return []


def evaluate_retrieval(
    questions: Sequence[RetrievalQuestion],
    fragments: Sequence[Fragment] | None = None,
) -> list[Result]:
    """Score each question by hash-cosine retrieval over its fragments.

    Args:
        questions: Labeled questions (text, ``expected_id``, ``rejected_id``).
            A question may carry its own ``fragments``.
        fragments: Shared fragment set used when a question has none.

    Returns:
        One result per question. The question passes when ``expected_id`` is
        among the hits and ``rejected_id`` is not. An empty hit list is a
        failure of that question when its expected fragment is in the set.

    Raises:
        ValueError: If ``questions`` is empty ("набор пуст").
    """
    if len(questions) == 0:
        raise ValueError("набор пуст")

    results: list[Result] = []
    for item in questions:
        catalog = _catalog(item, fragments)
        expected_id = item["expected_id"]
        rejected_id = item["rejected_id"]
        found_ids = tuple(search_fragments(item["question"], catalog))
        expected_in_set = any(fragment["id"] == expected_id for fragment in catalog)
        if not found_ids and expected_in_set:
            results.append(
                Result(
                    question=item["question"],
                    expected_id=expected_id,
                    rejected_id=rejected_id,
                    found_ids=found_ids,
                    passed=False,
                    error="пустая выдача",
                )
            )
            continue

        passed = expected_id in found_ids and rejected_id not in found_ids
        results.append(
            Result(
                question=item["question"],
                expected_id=expected_id,
                rejected_id=rejected_id,
                found_ids=found_ids,
                passed=passed,
                error=None if passed else "нужный фрагмент не найден или чужой попал в выдачу",
            )
        )
    return results
