"""Email draft business logic (CRUD + mark-sent + LLM generation)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.email_draft import EmailDraft
from app.models.enums import EmailGoal
from app.schemas.email_draft import EmailDraftCreate, EmailDraftUpdate, EmailGenerationRequest
from app.services.email_generator import EmailGenerator
from app.services.exceptions import NotFoundError
from app.services.person_service import PersonService

if TYPE_CHECKING:
    from app.services.company_service import CompanyService


class EmailDraftService:
    """CRUD operations for `EmailDraft` using an injected async session."""

    def __init__(
        self,
        db: AsyncSession,
        email_generator: EmailGenerator | None = None,
    ) -> None:
        self.db = db
        self._email_generator = email_generator

    async def create(self, data: EmailDraftCreate) -> EmailDraft:
        """Insert a draft. Raises NotFoundError if person_id does not exist."""
        person = await PersonService(self.db).get_by_id(data.person_id)
        if person is None:
            raise NotFoundError(f"Person '{data.person_id}' not found")

        payload = data.model_dump()
        if payload.get("goal") is None:
            payload["goal"] = EmailGoal.INTRO

        draft = EmailDraft(**payload)
        self.db.add(draft)
        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    async def get_by_id(self, draft_id: UUID) -> EmailDraft | None:
        """Return a draft by primary key, or None."""
        result = await self.db.execute(select(EmailDraft).where(EmailDraft.id == draft_id))
        return result.scalar_one_or_none()

    async def get_with_person(self, draft_id: UUID) -> EmailDraft | None:
        """Load a draft and its person in one extra SELECT (selectinload)."""
        result = await self.db.execute(
            select(EmailDraft)
            .options(selectinload(EmailDraft.person))
            .where(EmailDraft.id == draft_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        limit: int = 20,
        offset: int = 0,
        person_id: UUID | None = None,
    ) -> tuple[list[EmailDraft], int]:
        """Return a page of drafts, optionally filtered by person."""
        filters = []
        if person_id is not None:
            filters.append(EmailDraft.person_id == person_id)

        total_result = await self.db.execute(
            select(func.count()).select_from(EmailDraft).where(*filters)
        )
        total = total_result.scalar_one()

        result = await self.db.execute(
            select(EmailDraft)
            .where(*filters)
            .order_by(EmailDraft.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def update(self, draft_id: UUID, data: EmailDraftUpdate) -> EmailDraft | None:
        """Apply a partial update. Returns None if the draft does not exist."""
        draft = await self.get_by_id(draft_id)
        if draft is None:
            return None

        updates = data.model_dump(exclude_unset=True)
        if "person_id" in updates and updates["person_id"] is not None:
            person = await PersonService(self.db).get_by_id(updates["person_id"])
            if person is None:
                raise NotFoundError(f"Person '{updates['person_id']}' not found")

        for field, value in updates.items():
            setattr(draft, field, value)

        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    async def delete(self, draft_id: UUID) -> bool:
        """Delete by id. Returns True if a row was removed."""
        draft = await self.get_by_id(draft_id)
        if draft is None:
            return False
        await self.db.delete(draft)
        await self.db.commit()
        return True

    async def mark_sent(self, draft_id: UUID) -> EmailDraft | None:
        """Set is_sent and sent_at in the application (UTC). Returns None if missing."""
        draft = await self.get_by_id(draft_id)
        if draft is None:
            return None
        draft.is_sent = True
        draft.sent_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    @property
    def email_generator(self) -> EmailGenerator:
        """Lazy default so tests can inject a fake generator."""
        if self._email_generator is None:
            self._email_generator = EmailGenerator()
        return self._email_generator

    async def generate_and_save(
        self,
        person_id: UUID,
        request: EmailGenerationRequest,
        person_service: PersonService,
        company_service: CompanyService,
    ) -> tuple[EmailDraft, dict[str, Any]]:
        """Generate a draft via LLM, persist it, return (draft, metadata)."""
        person = await person_service.get_by_id(person_id)
        if person is None:
            raise NotFoundError(f"Person {person_id} not found")

        company = None
        if person.company_id is not None:
            company = await company_service.get_by_id(person.company_id)

        meta = await self.email_generator.generate(person, company, request)
        draft = EmailDraft(
            person_id=person.id,
            subject=meta["subject"],
            body=meta["body"],
            goal=request.goal,
            generation_context={
                "rag_context_used": meta.get("rag_context_used") or [],
                "model": meta.get("model"),
                "tokens_input": meta.get("tokens_input"),
                "tokens_output": meta.get("tokens_output"),
                "estimated_cost_usd": meta.get("estimated_cost_usd"),
                "validation_errors": meta.get("validation_errors") or [],
                "retried": meta.get("retried", False),
                "sender_name": request.sender_name,
                "sender_title": request.sender_title,
                "sender_company": request.sender_company,
            },
        )
        self.db.add(draft)
        await self.db.commit()
        await self.db.refresh(draft)
        return draft, meta
