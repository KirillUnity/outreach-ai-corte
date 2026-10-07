"""EmailFinder orchestration with an in-memory session stand-in."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import EmailFinderSettings
from app.models.company import Company
from app.models.email_candidate import EmailCandidate, EmailCandidateSource
from app.models.enums import EmailStatus
from app.models.person import Person
from app.services.email_finder.finder import EmailFinder
from app.services.email_finder.smtp_verifier import SMTPVerifier
from app.core.config import Settings


class _MemDb:
    def __init__(self, person: SimpleNamespace, company: SimpleNamespace | None) -> None:
        self.person = person
        self.company = company
        self.rows: list[EmailCandidate] = []

    def add(self, row: EmailCandidate) -> None:
        self.rows.append(row)

    async def get(self, model, ident):  # type: ignore[no-untyped-def]
        if model is Person and ident == self.person.id:
            return self.person
        if model is Company and self.company is not None and ident == self.company.id:
            return self.company
        if model is EmailCandidate:
            return next((row for row in self.rows if row.id == ident), None)
        return None

    async def execute(self, _stmt):  # type: ignore[no-untyped-def]
        outer = self

        class _Result:
            def scalars(self):  # type: ignore[no-untyped-def]
                return self

            def all(self):  # type: ignore[no-untyped-def]
                return list(outer.rows)

        return _Result()

    async def commit(self) -> None:
        return None

    async def refresh(self, _row: EmailCandidate) -> None:
        return None

    async def delete(self, row: EmailCandidate) -> None:
        self.rows = [item for item in self.rows if item is not row]


def _person(*, email: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        first_name="John",
        last_name="Doe",
        email=email,
        email_status=EmailStatus.UNKNOWN,
        company_id=uuid4(),
    )


def _company(company_id) -> SimpleNamespace:
    return SimpleNamespace(id=company_id, domain="stripe.com")


def _finder(person: SimpleNamespace, company: SimpleNamespace | None = None) -> EmailFinder:
    company = company or _company(person.company_id)
    db = _MemDb(person, company)
    settings = SimpleNamespace(
        email_finder=EmailFinderSettings(enabled=True, hunter_enabled=False, smtp_enabled=False)
    )
    finder = EmailFinder(db, settings)  # type: ignore[arg-type]
    finder.hunter.enabled = False
    return finder


@pytest.mark.asyncio
async def test_find_for_person_creates_candidates() -> None:
    person = _person()
    finder = _finder(person)
    rows = await finder.find_for_person(person)  # type: ignore[arg-type]
    assert len(rows) >= 5
    assert any(row.pattern_used == "{first}.{last}" for row in rows)


@pytest.mark.asyncio
async def test_find_prefers_existing_linkedin_email() -> None:
    person = _person(email="john@stripe.com")
    finder = _finder(person)
    rows = await finder.find_for_person(person)  # type: ignore[arg-type]
    linkedin = next(row for row in rows if row.source == EmailCandidateSource.LINKEDIN)
    assert linkedin.confidence == 0.9
    assert linkedin.is_primary is True
    assert person.email == "john@stripe.com"


@pytest.mark.asyncio
async def test_find_marks_primary_by_max_confidence() -> None:
    person = _person()
    finder = _finder(person)

    async def hunter_hit(_fn: str, _ln: str, _domain: str):
        return [{"email": "john.doe@stripe.com", "confidence": 0.9, "source": "hunter", "raw": {}}]

    finder.hunter.enabled = True
    finder.hunter.find_email = hunter_hit  # type: ignore[method-assign]
    rows = await finder.find_for_person(person, use_hunter=True)  # type: ignore[arg-type]
    primary = next(row for row in rows if row.is_primary)
    assert primary.source == EmailCandidateSource.HUNTER
    assert primary.confidence == 0.9


@pytest.mark.asyncio
async def test_find_updates_person_email() -> None:
    person = _person()
    finder = _finder(person)
    await finder.find_for_person(person)  # type: ignore[arg-type]
    assert person.email
    assert "@stripe.com" in person.email


@pytest.mark.asyncio
async def test_find_does_not_duplicate_existing_candidates() -> None:
    person = _person()
    finder = _finder(person)
    first = await finder.find_for_person(person)  # type: ignore[arg-type]
    second = await finder.find_for_person(person)  # type: ignore[arg-type]
    emails = [row.email for row in second]
    assert len(emails) == len(set(emails))
    assert len(second) == len(first)


@pytest.mark.asyncio
async def test_set_primary_updates_person() -> None:
    person = _person()
    finder = _finder(person)
    rows = await finder.find_for_person(person)  # type: ignore[arg-type]
    other = next(row for row in rows if not row.is_primary)
    updated = await finder.set_primary(other.id)
    assert updated.is_primary is True
    assert person.email == other.email
    assert sum(1 for row in finder.db.rows if row.is_primary) == 1  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_finder_creates_apollo_candidate() -> None:
    person = _person()
    finder = _finder(person)

    async def apollo_hit(_fn: str, _ln: str, _domain: str):
        return [{"email": "ada.unique@stripe.com", "confidence": 0.85, "source": "apollo", "raw": {}}]

    finder.apollo.enabled = True
    finder.apollo.match_person = apollo_hit  # type: ignore[method-assign]
    rows = await finder.find_for_person(person, use_apollo=True)  # type: ignore[arg-type]
    assert any(row.source == EmailCandidateSource.APOLLO for row in rows)
    assert any(row.email == "ada.unique@stripe.com" for row in rows)


@pytest.mark.asyncio
async def test_smtp_verifier_disabled_never_probes_network() -> None:
    result = await SMTPVerifier(Settings()).verify("lead@example.com")
    assert result == {"status": "unknown", "reason": "SMTP disabled", "mx_host": None}
