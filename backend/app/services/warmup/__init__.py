"""Mailbox warmup emulator (simulated engagement, no SMTP)."""

from app.services.warmup.warmup_emulator import WarmupEmulator
from app.services.warmup.warmup_service import WarmupService

__all__ = ["WarmupEmulator", "WarmupService"]
