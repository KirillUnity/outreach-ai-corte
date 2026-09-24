"""OutputValidator — no network."""

from app.services.output_validator import OutputValidator


def test_valid_email() -> None:
    ok, errors = OutputValidator().validate_email(
        "Idea for your billing team",
        "I noticed your invoicing API and wanted to compare notes for fifteen minutes.",
        max_words=120,
    )
    assert ok
    assert errors == []


def test_rejects_empty_subject() -> None:
    ok, errors = OutputValidator().validate_email(
        "  ",
        "A real body with enough words to pass the length check.",
        max_words=120,
    )
    assert not ok
    assert "subject is empty" in errors


def test_rejects_spam_words() -> None:
    ok, errors = OutputValidator().validate_email(
        "Limited time offer",
        "We guarantee free results if you act now.",
        max_words=120,
    )
    assert not ok
    assert any("spam" in error for error in errors)


def test_rejects_all_caps() -> None:
    ok, errors = OutputValidator().validate_email(
        "HELLO THERE FRIEND",
        "This body is fine and does not shout.",
        max_words=120,
    )
    assert not ok
    assert any("ALL CAPS" in error for error in errors)


def test_rejects_forbidden_phrase() -> None:
    ok, errors = OutputValidator().validate_email(
        "Quick note",
        "I hope this email finds you well. Can we talk next week?",
        max_words=120,
    )
    assert not ok
    assert any("forbidden phrase" in error for error in errors)
