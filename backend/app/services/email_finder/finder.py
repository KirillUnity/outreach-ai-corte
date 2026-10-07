"""Orchestrate LinkedIn / Hunter / patterns into EmailCandidate rows."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.company import Company
from app.models.email_candidate import EmailCandidate, EmailCandidateSource, EmailCandidateStatus
from app.models.enums import EmailStatus
from app.models.person import Person
from app.services.exceptions import NotFoundError
from app.services.email_finder.apollo_client import ApolloClient
from app.services.email_finder.hunter_client import HunterClient
from app.services.email_finder.pattern_generator import PatternGenerator
from app.services.email_finder.smtp_verifier import SMTPVerifier

logger = logging.getLogger(__name__)


class EmailFinder:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.pattern_gen = PatternGenerator(settings.email_finder.common_patterns)
        self.smtp = SMTPVerifier(settings)
        self.hunter = HunterClient(settings)
        self.apollo = ApolloClient(settings)

    async def find_for_person(
        self,
        person: Person,
        domain: str | None = None,
        use_hunter: bool = True,
        use_smtp: bool = False,
        use_apollo: bool = True,
    ) -> list[EmailCandidate]:
        if not self.settings.email_finder.enabled:
            return await self.get_candidates(person.id)

        host = await self._resolve_domain(person, domain)
        existing = {row.email.lower(): row for row in await self.get_candidates(person.id)}
        created: list[EmailCandidate] = []
        cfg = self.settings.email_finder

        if person.email:
            created.append(
                await self._upsert(
                    person,
                    existing,
                    email=person.email,
                    source=EmailCandidateSource.LINKEDIN,
                    confidence=0.9,
                    status=EmailCandidateStatus.UNKNOWN,
                    pattern_used=None,
                    raw=None,
                )
            )

        if use_hunter and host and self.hunter.enabled:
            hits = await self.hunter.find_email(person.first_name, person.last_name, host)
            for hit in hits:
                created.append(
                    await self._upsert(
                        person,
                        existing,
                        email=str(hit["email"]),
                        source=EmailCandidateSource.HUNTER,
                        confidence=float(hit["confidence"]),
                        status=EmailCandidateStatus.UNKNOWN,
                        pattern_used=None,
                        raw=hit.get("raw") if isinstance(hit.get("raw"), dict) else None,
                    )
                )

        if use_apollo and host and self.apollo.enabled:
            hits = await self.apollo.match_person(person.first_name, person.last_name, host)
            for hit in hits:
                created.append(
                    await self._upsert(
                        person,
                        existing,
                        email=str(hit["email"]),
                        source=EmailCandidateSource.APOLLO,
                        confidence=float(hit["confidence"]),
                        status=EmailCandidateStatus.UNKNOWN,
                        pattern_used=None,
                        raw=hit.get("raw") if isinstance(hit.get("raw"), dict) else None,
                    )
                )

        if host:
            patterns = self.pattern_gen.generate(person.first_name, person.last_name, host)
            for item in patterns[: cfg.max_patterns_to_try]:
                created.append(
                    await self._upsert(
                        person,
                        existing,
                        email=str(item["email"]),
                        source=EmailCandidateSource.PATTERN,
                        confidence=float(item["confidence"]),
                        status=EmailCandidateStatus.PENDING,
                        pattern_used=str(item["pattern"]),
                        raw=None,
                    )
                )

        rows = [row for row in created if row is not None]
        if use_smtp:
            for row in rows:
                details = await self.smtp.verify(row.email)
                self._apply_smtp(row, details)

        by_email = {
            row.email: row
            for row in created
            if row.confidence >= cfg.min_confidence_to_save
        }
        kept = sorted(by_email.values(), key=lambda item: item.confidence, reverse=True)
        for row in kept:
            row.is_primary = False
        if kept and kept[0].confidence >= cfg.min_confidence_to_use:
            kept[0].is_primary = True
            person.email = kept[0].email
            person.email_status = (
                EmailStatus.VALID if kept[0].status == EmailCandidateStatus.VERIFIED else EmailStatus.UNKNOWN
            )
            if kept[0].status == EmailCandidateStatus.INVALID:
                person.email_status = EmailStatus.INVALID
            elif kept[0].status == EmailCandidateStatus.CATCHALL:
                person.email_status = EmailStatus.CATCH_ALL

        await self.db.commit()
        return await self.get_candidates(person.id)

    async def get_candidates(self, person_id: UUID) -> list[EmailCandidate]:
        stmt = (
            select(EmailCandidate)
            .where(EmailCandidate.person_id == person_id)
            .order_by(EmailCandidate.confidence.desc(), EmailCandidate.created_at.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def set_primary(self, candidate_id: UUID) -> EmailCandidate:
        row = await self.db.get(EmailCandidate, candidate_id)
        if row is None:
            raise NotFoundError(f"Email candidate '{candidate_id}' not found")
        siblings = await self.get_candidates(row.person_id)
        for item in siblings:
            item.is_primary = item.id == row.id
        person = await self.db.get(Person, row.person_id)
        if person is not None:
            person.email = row.email
            person.email_status = EmailStatus.UNKNOWN
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def verify_existing(self, candidate_id: UUID) -> EmailCandidate:
        row = await self.db.get(EmailCandidate, candidate_id)
        if row is None:
            raise NotFoundError(f"Email candidate '{candidate_id}' not found")
        details = await self.smtp.verify(row.email)
        self._apply_smtp(row, details)
        row.verified_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def delete_candidate(self, candidate_id: UUID) -> bool:
        row = await self.db.get(EmailCandidate, candidate_id)
        if row is None:
            return False
        await self.db.delete(row)
        await self.db.commit()
        return True

    async def _resolve_domain(self, person: Person, domain: str | None) -> str | None:
        if domain:
            return domain.strip().lower()
        if person.company_id is None:
            return None
        company = await self.db.get(Company, person.company_id)
        return company.domain.lower() if company and company.domain else None

    async def _upsert(
        self,
        person: Person,
        existing: dict[str, EmailCandidate],
        *,
        email: str,
        source: EmailCandidateSource,
        confidence: float,
        status: EmailCandidateStatus,
        pattern_used: str | None,
        raw: dict | None,
    ) -> EmailCandidate:
        key = email.strip().lower()
        if key in existing:
            row = existing[key]
            if confidence > row.confidence:
                row.confidence = confidence
                row.source = source
                row.pattern_used = pattern_used or row.pattern_used
            return row
        now = datetime.now(timezone.utc)
        row = EmailCandidate(
            person_id=person.id,
            email=key,
            source=source,
            status=status,
            confidence=confidence,
            pattern_used=pattern_used,
            is_primary=False,
            raw_provider_data=raw,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        existing[key] = row
        return row

    def _apply_smtp(self, row: EmailCandidate, details: dict) -> None:
        status = str(details.get("status") or "unknown")
        mapping = {
            "valid": EmailCandidateStatus.VERIFIED,
            "invalid": EmailCandidateStatus.INVALID,
            "catchall": EmailCandidateStatus.CATCHALL,
            "unknown": EmailCandidateStatus.UNKNOWN,
        }
        row.status = mapping.get(status, EmailCandidateStatus.UNKNOWN)
        row.verification_details = details
        if row.status == EmailCandidateStatus.VERIFIED:
            row.confidence = min(1.0, row.confidence + 0.1)
        elif row.status == EmailCandidateStatus.INVALID:
            row.confidence = 0.0
        elif row.status == EmailCandidateStatus.CATCHALL:
            row.confidence = min(row.confidence, 0.3)
