"""Node unit tests with fake services."""

from types import SimpleNamespace
from uuid import uuid4

from app.core.config import AgentSettings, Settings
from app.services.agent.nodes import decide, load_person_and_company


class _MissingPerson:
    async def get_by_id(self, _id):
        return None


def test_decide_rejects_on_validation_errors() -> None:
    settings = Settings(
        agent=AgentSettings(require_human_approval=False, require_deliverability_check=False)
    )
    out = decide({"validation_errors": ["spam trigger words"]}, settings)
    assert out["decision"] == "reject"
    assert "validation" in (out["decision_reason"] or "")


def test_decide_holds_on_deliverability_fail() -> None:
    settings = Settings(
        agent=AgentSettings(require_human_approval=False, require_deliverability_check=True)
    )
    out = decide({"validation_errors": [], "deliverability_ok": False}, settings)
    assert out["decision"] == "hold"
    assert "deliverability" in (out["decision_reason"] or "")


def test_decide_sends_when_all_ok() -> None:
    settings = Settings(
        agent=AgentSettings(require_human_approval=False, require_deliverability_check=False)
    )
    out = decide({"validation_errors": [], "deliverability_ok": True}, settings)
    assert out["decision"] == "send"


async def test_load_person_not_found_adds_error() -> None:
    state = {"person_id": uuid4()}
    update = await load_person_and_company(state, _MissingPerson(), SimpleNamespace())
    assert update["errors"]
    assert "not found" in update["errors"][0]
