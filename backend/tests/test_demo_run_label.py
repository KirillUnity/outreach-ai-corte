"""Study-run label and cost. No network and no cloud tokens."""

from types import SimpleNamespace
from uuid import uuid4

from app.api.routers.agent import _from_row, _from_state
from app.core.config import AgentSettings, LLMSettings, Settings
from app.services.agent.nodes import decide, generate_email_node
from app.services.cost_tracker import CostTracker
from app.services.email_generator import EmailGenerator
from app.services.llm_client import LLMClient, STUDY_RUN_NOTE
from app.services.rag_service import RAGService

_MOCK_SUBJECT = "Quick idea for your team"


class _People:
    def __init__(self, person: SimpleNamespace) -> None:
        self.person = person

    async def get_by_id(self, _person_id):  # type: ignore[no-untyped-def]
        return self.person


class _Companies:
    async def get_by_id(self, _company_id):  # type: ignore[no-untyped-def]
        return None


def _person() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        first_name="Ada",
        last_name="Lovelace",
        title="Head of Finance",
        email=None,
        company_id=None,
    )


def _graph_state(person_id) -> dict:  # type: ignore[no-untyped-def]
    return {
        "person_id": person_id,
        "goal": "meeting",
        "sender_name": "Kirill",
        "sender_title": "Founder",
        "sender_company": "Northwind",
        "language": "en",
        "max_words": 120,
        "iteration": 0,
        "total_tokens_input": 0,
        "total_tokens_output": 0,
        "total_cost_usd": 0.0,
        "email_found": False,
        "graph_context": {},
    }


def _approval_settings() -> Settings:
    return Settings(
        agent=AgentSettings(require_human_approval=True, require_deliverability_check=True)
    )


def test_priced_models_stay_on_the_table() -> None:
    tracker = CostTracker()
    assert tracker.estimate_chat("gpt-4o-mini", 1_000_000, 0) == 0.15
    assert tracker.estimate_chat("gpt-4o", 1_000_000, 0) == 2.5
    assert tracker.estimate_chat("openai/gpt-4o-mini", 1_000_000, 0) == 0.15
    assert tracker.estimate_chat("openai/gpt-4o", 1_000_000, 0) == 2.5
    assert tracker.estimate_chat("mock-gpt-4o-mini", 1_000_000, 1_000_000) == 0.0


async def test_mock_run_is_free_and_labeled() -> None:
    settings = Settings(llm_mode="mock")
    tracker = CostTracker()
    client = LLMClient(settings, cost_tracker=tracker)
    assert client._client is None

    raw = await client.chat_json("Write a short cold email.", "Ada at Acme, Head of Finance")
    assert raw["run_note"] == STUDY_RUN_NOTE
    assert raw["parsed"]["subject"] == _MOCK_SUBJECT
    assert raw["parsed"]["body"]
    assert tracker.total_usd == 0.0

    person = _person()
    generator = EmailGenerator(
        settings,
        llm_client=client,
        cost_tracker=tracker,
        rag_service=RAGService(settings),
    )
    update = await generate_email_node(_graph_state(person.id), generator, _People(person), _Companies())
    assert update["email_subject"]
    assert update["email_body"]
    assert update["run_note"] == STUDY_RUN_NOTE
    assert update["total_cost_usd"] == 0.0
    assert tracker.total_usd == 0.0

    decision = decide(
        {
            "validation_errors": [],
            "guardrail_results": [],
            "deliverability_ok": True,
        },
        _approval_settings(),
    )
    assert decision["decision"] == "hold"
    assert decision["decision_reason"] == "awaiting approval"

    response = _from_state(
        {
            **update,
            **decision,
            "total_cost_usd": update["total_cost_usd"],
        }
    )
    assert response.email_subject
    assert response.email_body
    assert response.decision == "hold"
    assert response.estimated_cost_usd == 0.0
    assert response.run_note == "учебный прогон, модель не вызывалась"


async def test_real_client_error_is_not_replaced_with_mock_draft() -> None:
    class _BoomCompletions:
        async def create(self, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("cloud chat failed")

    settings = Settings(
        llm=LLMSettings(mode="real", openai_api_key="sk-test"),
        llm_mode="real",
        openai_api_key="sk-test",
    )
    fake = SimpleNamespace(chat=SimpleNamespace(completions=_BoomCompletions()))
    client = LLMClient(settings, client=fake, backoff_seconds=0.0)
    generator = EmailGenerator(settings, llm_client=client, rag_service=RAGService(settings))
    person = _person()
    update = await generate_email_node(_graph_state(person.id), generator, _People(person), _Companies())

    assert update["errors"]
    assert "generate failed" in update["errors"][0]
    assert "cloud chat failed" in update["errors"][0]
    assert "email_subject" not in update
    assert "email_body" not in update
    assert _MOCK_SUBJECT not in str(update)
    assert update.get("run_note") != STUDY_RUN_NOTE
    assert settings.llm.mode == "real"


def test_saved_run_without_note_does_not_crash() -> None:
    row = SimpleNamespace(
        final_state={"email_subject": "Hi", "email_body": "Hello there"},
        decision="hold",
        decision_reason="awaiting approval",
        tokens_input=3,
        tokens_output=4,
        cost_usd=0.01,
        iterations=1,
        created_at=None,
    )
    loaded = _from_row(row)
    assert loaded.run_note is None
    assert loaded.email_subject == "Hi"
    assert loaded.decision == "hold"
    assert loaded.estimated_cost_usd == 0.01
