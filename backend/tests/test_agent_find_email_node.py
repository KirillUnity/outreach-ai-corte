"""find_email LangGraph node — skip, lookup, empty results."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.enums import EmailStatus
from app.services.agent.nodes import find_email_node


class _PersonService:
    def __init__(self, person) -> None:
        self.person = person

    async def get_by_id(self, person_id):
        if self.person is not None and person_id == self.person.id:
            return self.person
        return None


def _state(person_id):
    return {
        "person_id": person_id,
        "company_data": {"domain": "stripe.com"},
        "errors": [],
    }


@pytest.mark.asyncio
async def test_find_email_skips_if_person_has_email() -> None:
    person = SimpleNamespace(
        id=uuid4(),
        email="john@stripe.com",
        email_status=EmailStatus.UNKNOWN,
    )
    finder = AsyncMock()
    out = await find_email_node(_state(person.id), _PersonService(person), finder)
    finder.find_for_person.assert_not_called()
    assert out["email_found"] is True
    assert out["email_address"] == "john@stripe.com"
    assert out["email_source"] == "linkedin"


@pytest.mark.asyncio
async def test_find_email_calls_finder_when_missing() -> None:
    person = SimpleNamespace(
        id=uuid4(),
        email=None,
        email_status=EmailStatus.UNKNOWN,
    )
    candidate = SimpleNamespace(
        email="john.doe@stripe.com",
        is_primary=True,
        confidence=0.85,
        source=SimpleNamespace(value="pattern"),
    )
    finder = AsyncMock()
    finder.find_for_person = AsyncMock(return_value=[candidate])
    out = await find_email_node(_state(person.id), _PersonService(person), finder)
    finder.find_for_person.assert_awaited_once()
    assert out["email_found"] is True
    assert out["email_address"] == "john.doe@stripe.com"
    assert out["email_candidates_count"] == 1


@pytest.mark.asyncio
async def test_find_email_handles_no_candidates() -> None:
    person = SimpleNamespace(
        id=uuid4(),
        email=None,
        email_status=EmailStatus.UNKNOWN,
    )
    finder = AsyncMock()
    finder.find_for_person = AsyncMock(return_value=[])
    out = await find_email_node(_state(person.id), _PersonService(person), finder)
    assert out["email_found"] is False
    assert out["email_candidates_count"] == 0
    assert "errors" not in out
