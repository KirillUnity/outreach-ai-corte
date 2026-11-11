"""Retrieval quality on teaching fragments. Hash cosine only, no model calls."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.rag_quality import Fragment, RetrievalQuestion, evaluate_retrieval

_FIXTURE = Path(__file__).parent / "fixtures" / "rag_questions.json"


def _questions() -> list[RetrievalQuestion]:
    payload = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return payload["questions"]


def test_fixture_keeps_expected_fragment_and_drops_rejected() -> None:
    results = evaluate_retrieval(_questions())
    assert results
    assert len(results) == len(_questions())
    for result in results:
        assert result.passed
        assert result.expected_id in result.found_ids
        assert result.rejected_id not in result.found_ids


def test_empty_question_list_is_refused() -> None:
    with pytest.raises(ValueError, match="набор пуст"):
        evaluate_retrieval([])


def test_empty_hits_for_known_fragment_are_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.rag_quality.search_fragments",
        lambda question, fragments: [],
    )
    fragments: list[Fragment] = [
        {
            "id": "pricing-startups",
            "text": "Pricing starts at a simple monthly fee for startups. Note 0.",
        },
        {
            "id": "office-ferns",
            "text": "The lobby keeps ferns that need water twice a week. Note 0.",
        },
    ]
    questions: list[RetrievalQuestion] = [
        {
            "question": "Какой ежемесячный тариф для стартапов?",
            "expected_id": "pricing-startups",
            "rejected_id": "office-ferns",
        }
    ]
    results = evaluate_retrieval(questions, fragments=fragments)
    assert len(results) == 1
    assert results[0].passed is False
    assert results[0].found_ids == ()
    assert results[0].error == "пустая выдача"
