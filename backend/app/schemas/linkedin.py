"""Schemas for LinkedIn profile enrichment."""

from pydantic import BaseModel, Field, field_validator

from app.schemas.company import CompanyResponse, normalize_domain
from app.schemas.person import PersonResponse, normalize_linkedin_url


class LinkedInProfile(BaseModel):
    """Normalized profile used by both mock and Phantombuster adapters."""

    linkedin_url: str
    username: str
    first_name: str
    last_name: str
    headline: str | None = None
    current_title: str | None = None
    current_company: str | None = None
    location: str | None = None
    about: str | None = None
    source: str = Field(description="mock | phantombuster")


class PersonResearchRequest(BaseModel):
    """POST /persons/research payload."""

    linkedin_url: str
    company_domain: str | None = None

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, value: str) -> str:
        """Same LinkedIn /in/ rules as PersonCreate."""
        return normalize_linkedin_url(value)

    @field_validator("company_domain")
    @classmethod
    def validate_company_domain(cls, value: str | None) -> str | None:
        """Optional domain, normalized like CompanyCreate."""
        if value is None:
            return None
        return normalize_domain(value)


class PersonResearchResponse(BaseModel):
    """Enrichment result. source is cache | mock | phantombuster."""

    person: PersonResponse
    company: CompanyResponse | None = None
    source: str
    research_duration_seconds: float
