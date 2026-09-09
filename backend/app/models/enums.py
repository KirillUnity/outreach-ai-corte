"""String enums shared by ORM models and Pydantic schemas."""

from enum import Enum


class EmailStatus(str, Enum):
    """Verification status of a person's email address."""

    UNKNOWN = "unknown"
    VALID = "valid"
    INVALID = "invalid"
    CATCH_ALL = "catch_all"
    RISKY = "risky"


class CompanySize(str, Enum):
    """Rough headcount bucket for a company."""

    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"


class EmailGoal(str, Enum):
    """Intent of a generated outreach draft."""

    INTRO = "intro"
    FOLLOW_UP = "follow_up"
    MEETING = "meeting"
    NURTURE = "nurture"
    BREAKUP = "breakup"
