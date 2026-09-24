"""HTTP + service tests for POST /persons/{id}/generate-email. LLM is always faked."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_db, get_email_generator
from app.api.routers.persons import router
from app.models.enums import EmailGoal, EmailStatus
from app.schemas.email_draft import EmailGenerationRequest
from app.services.email_draft_service import EmailDraftService
from app.services.exceptions import NotFoundError


class _FakeResult:
    def __init__(self, value) -> None:
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeSession:
    def __init__(self, person) -> None:
        self.person = person
        self.added = None

    async def execute(self, _stmt):
        return _FakeResult(self.person)

    def add(self, obj) -> None:
        now = datetime.now(timezone.utc)
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        obj.created_at = now
        obj.updated_at = now
        obj.is_sent = False
        obj.sent_at = None
        self.added = obj

    async def commit(self) -> None:
        return None

    async def refresh(self, _obj) -> None:
        return None


class _FakeGenerator:
    async def generate(self, person, company, request):
        return {
            "subject": "Idea for your billing team",
            "body": "I noticed your invoicing work and wanted 15 minutes to compare notes.",
            "rag_context_used": ["Stripe processes payments for platforms."],
            "tokens_input": 20,
            "tokens_output": 15,
            "estimated_cost_usd": 0.0,
            "model": "mock-gpt-4o-mini",
            "validation_errors": [],
            "retried": False,
        }


def _person():
    return SimpleNamespace(
        id=uuid4(),
        first_name="John",
        last_name="Doe",
        title="VP Sales",
        company_id=None,
        linkedin_url=None,
        email=None,
        email_status=EmailStatus.UNKNOWN,
        raw_linkedin_data=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _payload(person_id) -> dict:
    return {
        "person_id": str(person_id),
        "goal": "meeting",
        "tone": "professional",
        "max_words": 120,
        "language": "en",
        "sender_name": "Kirill",
        "sender_title": "Founder",
        "sender_company": "AI Cortex",
    }


def _app(session: _FakeSession) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_email_generator] = lambda: _FakeGenerator()
    return TestClient(app)


async def test_generate_email_success() -> None:
    person = _person()
    session = _FakeSession(person)
    service = EmailDraftService(session, email_generator=_FakeGenerator())
    request = EmailGenerationRequest(
        person_id=person.id,
        sender_name="Kirill",
        sender_title="Founder",
        sender_company="AI Cortex",
        goal=EmailGoal.MEETING,
    )
    person_service = SimpleNamespace(get_by_id=lambda _id: _async(person))
    company_service = SimpleNamespace(get_by_id=lambda _id: _async(None))
    draft, meta = await service.generate_and_save(
        person_id=person.id,
        request=request,
        person_service=person_service,
        company_service=company_service,
    )
    assert draft.subject == "Idea for your billing team"
    assert meta["model"] == "mock-gpt-4o-mini"
    assert session.added is draft


def test_generate_email_person_not_found_404() -> None:
    missing = uuid4()
    client = _app(_FakeSession(person=None))
    response = client.post(f"/api/v1/persons/{missing}/generate-email", json=_payload(missing))
    assert response.status_code == 404


def test_generate_email_http_success() -> None:
    person = _person()
    client = _app(_FakeSession(person))
    response = client.post(f"/api/v1/persons/{person.id}/generate-email", json=_payload(person.id))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["draft"]["subject"]
    assert body["model"] == "mock-gpt-4o-mini"
    assert body["tokens_input"] == 20


def test_generate_email_person_id_mismatch_400() -> None:
    path_id = uuid4()
    body_id = uuid4()
    client = _app(_FakeSession(person=None))
    response = client.post(f"/api/v1/persons/{path_id}/generate-email", json=_payload(body_id))
    assert response.status_code == 400
    assert response.json()["detail"] == "person_id mismatch"


async def _async(value):
    return value


@pytest.mark.asyncio
async def test_generate_and_save_missing_person() -> None:
    session = _FakeSession(person=None)
    service = EmailDraftService(session, email_generator=_FakeGenerator())
    request = EmailGenerationRequest(
        person_id=uuid4(),
        sender_name="Kirill",
        sender_title="Founder",
        sender_company="AI Cortex",
    )
    person_service = SimpleNamespace(get_by_id=lambda _id: _async(None))
    company_service = SimpleNamespace(get_by_id=lambda _id: _async(None))
    with pytest.raises(NotFoundError):
        await service.generate_and_save(
            person_id=request.person_id,
            request=request,
            person_service=person_service,
            company_service=company_service,
        )
