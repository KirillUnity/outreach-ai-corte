"""Prompt templates used by generation services."""

from app.services.prompts.email_prompts import (
    SYSTEM_PROMPT_OUTREACH,
    USER_PROMPT_TEMPLATE,
    VALIDATION_RETRY_SUFFIX,
)

__all__ = [
    "SYSTEM_PROMPT_OUTREACH",
    "USER_PROMPT_TEMPLATE",
    "VALIDATION_RETRY_SUFFIX",
]
