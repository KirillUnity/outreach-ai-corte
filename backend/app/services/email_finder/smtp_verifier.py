"""SMTP mailbox probe — mock only. Live RCPT TO is a spam-intel pattern; do not enable."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import Settings

logger = logging.getLogger(__name__)

_CATCHALL_DOMAINS = {"gmail.com", "outlook.com", "yahoo.com", "hotmail.com", "live.com"}


class SMTPVerifier:
    """Never opens a real MX socket in this project."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def verify(self, email: str) -> dict[str, str | None]:
        if not self.settings.email_finder.smtp_enabled:
            return {"status": "unknown", "reason": "SMTP disabled", "mx_host": None}
        # Mock path only. A real HELO/MAIL FROM/RCPT TO loop against MX would
        # look like list-building to Google/Microsoft and can blacklist the IP.
        await asyncio.sleep(0)
        domain = (email.split("@")[-1] if "@" in email else "").lower()
        if domain in _CATCHALL_DOMAINS:
            return {
                "status": "catchall",
                "reason": "Mock mode: consumer mailbox providers treated as catch-all",
                "mx_host": f"mx.{domain}",
            }
        return {"status": "unknown", "reason": "Mock mode", "mx_host": None}
