"""PatternGenerator name normalization and pattern confidence."""

from app.core.config import EmailFinderSettings
from app.services.email_finder.pattern_generator import PatternGenerator


def _gen() -> PatternGenerator:
    return PatternGenerator(EmailFinderSettings().common_patterns)


def test_generate_10_patterns() -> None:
    rows = _gen().generate("John", "Doe", "acme.com")
    assert len(rows) == 10
    emails = {row["email"] for row in rows}
    assert "john.doe@acme.com" in emails
    assert "jdoe@acme.com" in emails


def test_confidence_first_last_is_highest() -> None:
    rows = _gen().generate("Jane", "Smith", "acme.com")
    by_pattern = {row["pattern"]: row["confidence"] for row in rows}
    assert by_pattern["{first}.{last}"] == 0.85
    assert by_pattern["{first}.{last}"] == max(by_pattern.values())


def test_transliterate_cyrillic() -> None:
    gen = PatternGenerator(["{first}.{last}"])
    rows = gen.generate("Иван", "Петров", "acme.com")
    assert rows[0]["email"] == "ivan.petrov@acme.com"
    assert gen._transliterate("иван") == "ivan"


def test_normalize_removes_accents() -> None:
    rows = PatternGenerator(["{first}.{last}"]).generate("José", "García", "acme.com")
    assert rows[0]["email"] == "jose.garcia@acme.com"


def test_handles_hyphenated_last_name() -> None:
    rows = PatternGenerator(["{first}.{last}"]).generate("Ann", "Smith-Jones", "acme.com")
    assert rows[0]["email"] == "ann.smith-jones@acme.com"
