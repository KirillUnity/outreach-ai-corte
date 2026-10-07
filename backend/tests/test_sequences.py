"""Sequence tick advances steps and never sends mail."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.outreach_sequence import (
    EnrollmentStatus,
    OutreachSequence,
    OutreachSequenceEnrollment,
    SequenceStatus,
)
from app.models.person import Person
from app.services.sequence_service import SequenceService


class _Db:
    def __init__(self) -> None:
        self.sequence = OutreachSequence(
            name="Intro",
            status=SequenceStatus.ACTIVE,
            steps=[
                {"delay_days": 0, "goal": "intro", "template_hint": "hi"},
                {"delay_days": 3, "goal": "meeting", "template_hint": "follow up"},
            ],
        )
        self.sequence.id = uuid4()
        self.enrollment = OutreachSequenceEnrollment(
            sequence_id=self.sequence.id,
            person_id=uuid4(),
            current_step=0,
            status=EnrollmentStatus.PENDING,
        )
        self.enrollment.id = uuid4()
        self.smtp_calls: list[str] = []

    async def get(self, model, ident):  # type: ignore[no-untyped-def]
        if model is OutreachSequence and ident == self.sequence.id:
            return self.sequence
        if model is Person:
            return SimpleNamespace(id=ident)
        return None

    async def execute(self, _stmt):  # type: ignore[no-untyped-def]
        outer = self

        class _Result:
            def scalars(self):  # type: ignore[no-untyped-def]
                return self

            def all(self):  # type: ignore[no-untyped-def]
                return [outer.enrollment]

            def scalar_one_or_none(self):  # type: ignore[no-untyped-def]
                return None

        return _Result()

    async def commit(self) -> None:
        return None

    async def refresh(self, _row) -> None:  # type: ignore[no-untyped-def]
        return None

    def add(self, _row) -> None:
        return None


@pytest.mark.asyncio
async def test_sequence_tick_does_not_send_email() -> None:
    db = _Db()
    service = SequenceService(db)  # type: ignore[arg-type]
    advanced, completed = await service.tick(db.sequence.id)
    assert advanced == 1
    assert completed == 0
    assert db.enrollment.current_step == 1
    assert db.enrollment.status == EnrollmentStatus.ACTIVE
    assert service.emails_sent == 0
    assert db.smtp_calls == []

    advanced, completed = await service.tick(db.sequence.id)
    assert completed == 1
    assert db.enrollment.status == EnrollmentStatus.COMPLETED
    assert service.emails_sent == 0
