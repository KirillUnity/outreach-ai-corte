"""Advance sequence enrollments in the database. Never sends mail."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outreach_sequence import (
    EnrollmentStatus,
    OutreachSequence,
    OutreachSequenceEnrollment,
    SequenceStatus,
)
from app.models.person import Person
from app.schemas.sequence import SequenceCreate
from app.services.exceptions import NotFoundError


class SequenceService:
    emails_sent: int

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.emails_sent = 0

    async def create(self, data: SequenceCreate) -> OutreachSequence:
        row = OutreachSequence(
            name=data.name,
            mailbox_id=data.mailbox_id,
            status=data.status,
            steps=[step.model_dump() for step in data.steps],
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def list(self, limit: int = 50, offset: int = 0) -> list[OutreachSequence]:
        stmt = (
            select(OutreachSequence)
            .order_by(OutreachSequence.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def enroll(self, sequence_id: UUID, person_id: UUID) -> OutreachSequenceEnrollment:
        sequence = await self.db.get(OutreachSequence, sequence_id)
        if sequence is None:
            raise NotFoundError(f"Sequence '{sequence_id}' not found")
        person = await self.db.get(Person, person_id)
        if person is None:
            raise NotFoundError(f"Person '{person_id}' not found")
        existing = (
            await self.db.execute(
                select(OutreachSequenceEnrollment).where(
                    OutreachSequenceEnrollment.sequence_id == sequence_id,
                    OutreachSequenceEnrollment.person_id == person_id,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        row = OutreachSequenceEnrollment(
            sequence_id=sequence_id,
            person_id=person_id,
            current_step=0,
            status=EnrollmentStatus.PENDING,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def tick(self, sequence_id: UUID) -> tuple[int, int]:
        """Move each active/pending enrollment one step. Returns (advanced, completed)."""
        sequence = await self.db.get(OutreachSequence, sequence_id)
        if sequence is None:
            raise NotFoundError(f"Sequence '{sequence_id}' not found")
        if sequence.status == SequenceStatus.PAUSED:
            return 0, 0
        steps = list(sequence.steps or [])
        step_count = len(steps)
        stmt = select(OutreachSequenceEnrollment).where(
            OutreachSequenceEnrollment.sequence_id == sequence_id,
            OutreachSequenceEnrollment.status.in_(
                [EnrollmentStatus.PENDING, EnrollmentStatus.ACTIVE]
            ),
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        advanced = 0
        completed = 0
        for row in rows:
            # Deliberately no SMTP / Instantly HTTP / EmailDraft.create.
            if row.status == EnrollmentStatus.PENDING:
                row.status = EnrollmentStatus.ACTIVE
            row.current_step += 1
            advanced += 1
            if step_count == 0 or row.current_step >= step_count:
                row.status = EnrollmentStatus.COMPLETED
                completed += 1
        await self.db.commit()
        return advanced, completed
