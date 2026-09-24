"""Compile + ainvoke the graph with every collaborator faked (no tokens, no DNS)."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.core.config import AgentSettings, Settings
from app.models.enums import EmailGoal
from app.services.agent.agent_service import empty_outreach_state
from app.services.agent.graph import build_outreach_graph
from app.services.output_validator import OutputValidator


class _Person:
    def __init__(self) -> None:
        self.id = uuid4()
        self.first_name = "John"
        self.last_name = "Doe"
        self.title = "VP Sales"
        self.company_id = uuid4()
        self.email = "john@stripe.com"


class _Company:
    def __init__(self, company_id) -> None:
        self.id = company_id
        self.domain = "stripe.com"
        self.name = "Stripe"
        self.raw_site_text = "Stripe builds payments APIs for platforms."


class _PersonService:
    def __init__(self, person) -> None:
        self.person = person

    async def get_by_id(self, person_id):
        if self.person is not None and person_id == self.person.id:
            return self.person
        return None


class _CompanyService:
    def __init__(self, company) -> None:
        self.company = company

    async def get_by_id(self, company_id):
        if self.company is not None and company_id == self.company.id:
            return self.company
        return None

    async def research(self, domain):
        raise AssertionError("research should be skipped when raw_site_text exists")


class _Rag:
    async def search(self, domain, query, top_k=5):
        return [{"text": "Stripe processes payments for platforms."}]


class _Generator:
    def _build_search_query(self, person, request, company=None) -> str:
        return f"{getattr(person, 'title', '')} {getattr(company, 'name', '')}"

    async def generate(self, person, company, request):
        return {
            "subject": "Idea for your billing team",
            "body": "I noticed your payments API and wanted 15 minutes to compare notes.",
            "tokens_input": 10,
            "tokens_output": 8,
            "estimated_cost_usd": 0.0,
            "rag_context_used": ["Stripe processes payments for platforms."],
        }


class _DraftService:
    def __init__(self) -> None:
        self.created = None
        self.marked = None

    async def create(self, data):
        now = datetime.now(timezone.utc)
        draft = SimpleNamespace(
            id=uuid4(),
            person_id=data.person_id,
            subject=data.subject,
            body=data.body,
            goal=data.goal,
            created_at=now,
            updated_at=now,
        )
        self.created = draft
        return draft

    async def mark_sent(self, draft_id):
        self.marked = draft_id
        return SimpleNamespace(id=draft_id)


class _Checker:
    async def check_domain(self, domain):
        return {"ok": True, "domain": domain, "reason": "forced ok"}


def _settings() -> Settings:
    return Settings(
        agent=AgentSettings(
            require_human_approval=False,
            require_deliverability_check=False,
            enable_checkpointing=False,
            max_iterations=8,
        )
    )


async def test_graph_full_happy_path() -> None:
    person = _Person()
    company = _Company(person.company_id)
    drafts = _DraftService()
    graph = build_outreach_graph(
        _PersonService(person),
        _CompanyService(company),
        _Rag(),
        _Generator(),
        OutputValidator(),
        _Checker(),
        drafts,
        _settings(),
    )
    state = empty_outreach_state(
        person.id,
        EmailGoal.MEETING.value,
        {"name": "Kirill", "title": "Founder", "company": "AI Cortex"},
    )
    result = await graph.ainvoke(state)
    assert result["decision"] == "send"
    assert result["email_subject"]
    assert result["draft_id"] == drafts.created.id
    assert drafts.marked == drafts.created.id
    assert result["iteration"] >= 1


async def test_graph_stops_on_person_not_found() -> None:
    missing = uuid4()
    drafts = _DraftService()
    graph = build_outreach_graph(
        _PersonService(None),
        _CompanyService(None),
        _Rag(),
        _Generator(),
        OutputValidator(),
        _Checker(),
        drafts,
        _settings(),
    )
    state = empty_outreach_state(
        missing,
        "meeting",
        {"name": "Kirill", "title": "Founder", "company": "AI Cortex"},
    )
    result = await graph.ainvoke(state)
    assert result.get("errors")
    assert drafts.created is None
    assert result.get("decision") in (None, "unknown")
