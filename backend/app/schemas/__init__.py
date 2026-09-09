"""Pydantic request/response schemas."""

from app.schemas.company import (
    CompanyCreate,
    CompanyListResponse,
    CompanyResponse,
    CompanyUpdate,
)
from app.schemas.domain_health import (
    DomainHealthCreate,
    DomainHealthListResponse,
    DomainHealthResponse,
    DomainHealthUpdate,
)
from app.schemas.email_draft import (
    EmailDraftCreate,
    EmailDraftListResponse,
    EmailDraftResponse,
    EmailDraftUpdate,
    EmailDraftWithPersonResponse,
)
from app.schemas.person import (
    PersonCompanyAssign,
    PersonCreate,
    PersonListResponse,
    PersonResponse,
    PersonUpdate,
    PersonWithCompanyResponse,
)

__all__ = [
    "CompanyCreate",
    "CompanyListResponse",
    "CompanyResponse",
    "CompanyUpdate",
    "DomainHealthCreate",
    "DomainHealthListResponse",
    "DomainHealthResponse",
    "DomainHealthUpdate",
    "EmailDraftCreate",
    "EmailDraftListResponse",
    "EmailDraftResponse",
    "EmailDraftUpdate",
    "EmailDraftWithPersonResponse",
    "PersonCompanyAssign",
    "PersonCreate",
    "PersonListResponse",
    "PersonResponse",
    "PersonUpdate",
    "PersonWithCompanyResponse",
]
