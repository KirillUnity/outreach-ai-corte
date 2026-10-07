"""SQLAlchemy ORM models. Importing this package registers all tables on Base.metadata."""

from app.models.agent_run import AgentRun
from app.models.base import Base
from app.models.company import Company
from app.models.crm_sync_event import CrmSyncEvent
from app.models.domain_health import DomainHealth
from app.models.email_candidate import EmailCandidate, EmailCandidateSource, EmailCandidateStatus
from app.models.email_draft import EmailDraft
from app.models.enums import CompanySize, EmailGoal, EmailStatus
from app.models.mailbox import Mailbox, MailboxStatus
from app.models.outreach_sequence import (
    EnrollmentStatus,
    OutreachSequence,
    OutreachSequenceEnrollment,
    SequenceStatus,
)
from app.models.person import Person
from app.models.seo_article import SEOArticle
from app.models.warmup_event import WarmupEvent, WarmupEventType

__all__ = [
    "AgentRun",
    "Base",
    "Company",
    "CompanySize",
    "CrmSyncEvent",
    "DomainHealth",
    "EmailCandidate",
    "EmailCandidateSource",
    "EmailCandidateStatus",
    "EmailDraft",
    "EmailGoal",
    "EmailStatus",
    "Mailbox",
    "MailboxStatus",
    "EnrollmentStatus",
    "OutreachSequence",
    "OutreachSequenceEnrollment",
    "SequenceStatus",
    "Person",
    "SEOArticle",
    "WarmupEvent",
    "WarmupEventType",
]
