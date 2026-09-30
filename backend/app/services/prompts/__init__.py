"""Prompt templates used by generation services."""

from app.services.prompts.email_prompts import (
    SYSTEM_PROMPT_OUTREACH,
    USER_PROMPT_TEMPLATE,
    USER_PROMPT_WITH_WARM_INTRO,
    VALIDATION_RETRY_SUFFIX,
)

__all__ = [
    "SYSTEM_PROMPT_OUTREACH",
    "USER_PROMPT_TEMPLATE",
    "USER_PROMPT_WITH_WARM_INTRO",
    "VALIDATION_RETRY_SUFFIX",
]
