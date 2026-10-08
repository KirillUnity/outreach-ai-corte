"""Optional Sentry init. An empty DSN or a disabled flag leaves the SDK untouched."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.config import Settings

logger = logging.getLogger(__name__)

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_PHONE = re.compile(
    r"(?<!\d)(?:\+\d{1,3}[\s.\-]?)?(?:\(\d{2,4}\)[\s.\-]?|\d{3}[\s.\-])\d{3}[\s.\-]\d{4}(?!\d)"
)
_SENSITIVE_KEYS = frozenset(
    {"email", "phone", "telephone", "mobile", "sender_email", "recipient_email"}
)


def scrub_pii(event: dict[str, Any], _hint: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Drop emails and phone numbers from a Sentry event before it is sent.

    Returns a scrubbed copy. On an unexpected shape, returns a placeholder so a
    bug in the scrubber cannot ship the raw event.
    """
    try:
        cleaned = _scrub(event)
    except Exception:
        logger.exception("sentry scrub failed; dropping event body")
        return {"message": "[sentry event dropped: scrub failed]"}
    if isinstance(cleaned, dict):
        return cleaned
    return {"message": "[sentry event dropped: scrub failed]"}


def configure_sentry(cfg: Settings) -> bool:
    """Initialize Sentry when enabled and a DSN is set.

    Returns True only when ``sentry_sdk.init`` ran. Empty DSN and
    ``sentry_enabled=false`` both skip init and never raise.
    """
    if not cfg.sentry_enabled or not cfg.sentry_dsn.strip():
        logger.info("sentry disabled (empty DSN or SENTRY_ENABLED=false)")
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
    except ImportError:
        logger.exception("sentry enabled but sentry-sdk is not installed")
        return False

    sample_rate = 0.1 if not cfg.debug else 1.0
    sentry_sdk.init(
        dsn=cfg.sentry_dsn,
        integrations=[FastApiIntegration()],
        traces_sample_rate=sample_rate,
        send_default_pii=False,
        include_local_variables=False,
        before_send=scrub_pii,
        environment="production" if not cfg.debug else "development",
    )
    logger.info("sentry enabled traces_sample_rate=%s", sample_rate)
    return True


def _scrub(value: Any, key: str | None = None) -> Any:
    if key is not None and key.lower() in _SENSITIVE_KEYS:
        return "[redacted]"
    if isinstance(value, str):
        redacted = _EMAIL.sub("[redacted-email]", value)
        return _PHONE.sub("[redacted-phone]", redacted)
    if isinstance(value, dict):
        return {str(child_key): _scrub(child, str(child_key)) for child_key, child in value.items()}
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    if isinstance(value, tuple):
        return [_scrub(item) for item in value]
    return value
