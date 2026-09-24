"""Unit tests for EmailGenerator helpers — no network, no LLM."""

from types import SimpleNamespace
from uuid import uuid4

from app.schemas.email_draft import EmailGenerationRequest
from app.services.email_generator import EmailGenerator


def _request(**kwargs) -> EmailGenerationRequest:
    payload = {
        "person_id": uuid4(),
        "sender_name": "Kirill",
        "sender_title": "Founder",
        "sender_company": "AI Cortex",
    }
    payload.update(kwargs)
    return EmailGenerationRequest(**payload)


def test_build_search_query_includes_title_and_company() -> None:
    generator = EmailGenerator()
    person = SimpleNamespace(title="VP Sales", first_name="Ada", last_name="Lovelace")
    company = SimpleNamespace(name="Stripe")
    request = _request(custom_instructions="mention invoicing APIs")
    query = generator._build_search_query(person, request, company)
    assert "VP Sales" in query
    assert "Stripe" in query
    assert "invoicing APIs" in query


def test_contains_spam_words_detects_guarantee() -> None:
    generator = EmailGenerator()
    assert generator._contains_spam_words("We guarantee results")


def test_contains_spam_words_case_insensitive() -> None:
    generator = EmailGenerator()
    assert generator._contains_spam_words("LIMITED TIME offer")


def test_contains_spam_words_clean_text() -> None:
    generator = EmailGenerator()
    assert not generator._contains_spam_words(
        "I noticed your billing API and wanted to compare notes next week."
    )
