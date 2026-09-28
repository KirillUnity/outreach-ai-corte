"""Timeouts, retries, and jitter — never retry auth or bad requests."""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_RETRYABLE = frozenset({"RateLimitError", "APITimeoutError", "APIConnectionError"})
_FATAL = frozenset({"AuthenticationError", "BadRequestError", "PermissionDeniedError"})


class RetryPolicy:
    """Exponential backoff with optional full jitter (AWS builders-library pattern)."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        jitter: bool = True,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self._sleep = sleep or asyncio.sleep

    def compute_delay(self, attempt: int) -> float:
        """`attempt` is 0-based (delay after the first failure)."""
        delay = min(self.base_delay * (2**attempt), self.max_delay)
        if self.jitter:
            delay *= 0.5 + random.random()
        return delay

    def is_retryable(self, exc: BaseException) -> bool:
        name = type(exc).__name__
        if name in _FATAL:
            return False
        if name in _RETRYABLE:
            return True
        try:
            from openai import APIConnectionError, APITimeoutError, RateLimitError
        except ImportError:
            return False
        return isinstance(exc, RateLimitError | APITimeoutError | APIConnectionError)

    async def execute(self, func: Callable[..., Awaitable[T] | T], *args: Any, **kwargs: Any) -> T:
        """Run `func` until it succeeds or a non-retryable error / attempt budget."""
        last: BaseException | None = None
        for attempt in range(self.max_attempts):
            try:
                result = func(*args, **kwargs)
                if hasattr(result, "__await__"):
                    result = await result  # type: ignore[misc]
                return result  # type: ignore[return-value]
            except Exception as exc:
                last = exc
                retry = self.is_retryable(exc) and attempt < self.max_attempts - 1
                logger.warning(
                    "retry attempt=%s/%s retryable=%s error=%s",
                    attempt + 1,
                    self.max_attempts,
                    retry,
                    exc,
                )
                if not retry:
                    raise
                delay = self.compute_delay(attempt)
                if delay:
                    await self._sleep(delay)
        raise last or RuntimeError("retry exhausted")


class RetryPolicyFactory:
    """Named presets so call sites do not invent magic numbers."""

    @staticmethod
    def for_llm() -> RetryPolicy:
        return RetryPolicy(max_attempts=3, base_delay=1.0, max_delay=30.0, jitter=True)

    @staticmethod
    def for_http() -> RetryPolicy:
        return RetryPolicy(max_attempts=2, base_delay=0.5, max_delay=8.0, jitter=True)

    @staticmethod
    def for_db() -> RetryPolicy:
        return RetryPolicy(max_attempts=3, base_delay=0.1, max_delay=2.0, jitter=True)
