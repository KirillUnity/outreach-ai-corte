"""Heuristic QualityScorer — no LLM, no Langfuse."""

from app.services.agent.scoring import QualityScorer


def _words(n: int, extra: str = "") -> str:
    filler = " ".join(["word"] * n)
    return f"{extra} {filler}".strip()


def test_score_email_perfect() -> None:
    body = _words(
        90,
        extra="Jane at Acme — would you have 15 minutes next week to compare notes?",
    )
    scores = QualityScorer().score_email(
        "Idea for Acme",
        body,
        recipient_name="Jane Doe",
        company_name="Acme",
    )
    assert scores["length_score"] == 1.0
    assert scores["spam_score"] == 1.0
    assert scores["personalization_score"] == 1.0
    assert scores["cta_score"] == 1.0


def test_score_email_no_personalization() -> None:
    body = _words(90, extra="Would you have 15 minutes next week?")
    scores = QualityScorer().score_email(
        "Quick intro",
        body,
        recipient_name="Jane",
        company_name="Acme",
    )
    assert scores["personalization_score"] == 0.0
    assert scores["cta_score"] == 1.0


def test_score_email_with_spam_words() -> None:
    body = _words(90, extra="FREE guarantee — click here Jane at Acme")
    scores = QualityScorer().score_email(
        "Act now",
        body,
        recipient_name="Jane",
        company_name="Acme",
    )
    assert scores["spam_score"] < 1.0
    assert scores["personalization_score"] == 1.0
