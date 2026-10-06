"""Optional in-process loop for warmup ticks (off by default)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from app.core.config import Settings
from app.services.warmup.warmup_emulator import WarmupEmulator

logger = logging.getLogger(__name__)

SessionMaker = Callable[[], Any]


class WarmupScheduler:
    """Background `tick_all` loop. Prefer n8n Cron in production."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self, db_session_maker: SessionMaker) -> None:
        if not self.settings.warmup.enabled or not self.settings.warmup.auto_run_enabled:
            logger.info("warmup scheduler idle (enabled=%s auto_run=%s)", self.settings.warmup.enabled, self.settings.warmup.auto_run_enabled)
            return
        if self._task is not None and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop(db_session_maker), name="warmup-scheduler")
        logger.info("warmup scheduler started interval=%ss", self.settings.warmup.tick_interval_seconds)

    async def _run_loop(self, db_session_maker: SessionMaker) -> None:
        while self._running:
            try:
                async with db_session_maker() as db:
                    emulator = WarmupEmulator(db, self.settings)
                    result = await emulator.tick_all()
                    logger.info("warmup tick_all %s", result)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("warmup tick_all failed")
            await asyncio.sleep(self.settings.warmup.tick_interval_seconds)

    async def stop(self) -> None:
        self._running = False
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("warmup scheduler stopped")
