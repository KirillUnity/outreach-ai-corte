"""RetryPolicy unit tests — no network."""

from __future__ import annotations

import pytest

from app.services.retry_policy import RetryPolicy, RetryPolicyFactory


class RateLimitError(Exception):
    """Name must match OpenAI's exception so RetryPolicy retries."""


class AuthenticationError(Exception):
    """Fatal — never retry."""


async def test_retry_on_rate_limit() -> None:
    calls = {"n": 0}

    async def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 2:
            raise RateLimitError("slow down")
        return "ok"

    policy = RetryPolicy(max_attempts=3, base_delay=0.0, jitter=False)
    assert await policy.execute(flaky) == "ok"
    assert calls["n"] == 2


async def test_no_retry_on_auth_error() -> None:
    async def boom() -> None:
        raise AuthenticationError("bad key")

    policy = RetryPolicy(max_attempts=5, base_delay=0.0, jitter=False)
    with pytest.raises(AuthenticationError):
        await policy.execute(boom)


async def test_exponential_backoff_timing() -> None:
    delays: list[float] = []

    async def sleeper(delay: float) -> None:
        delays.append(delay)

    calls = {"n": 0}

    async def always_rate() -> None:
        calls["n"] += 1
        raise RateLimitError("nope")

    policy = RetryPolicy(max_attempts=3, base_delay=1.0, max_delay=30.0, jitter=False, sleep=sleeper)
    with pytest.raises(RateLimitError):
        await policy.execute(always_rate)
    assert delays == [1.0, 2.0]


def test_jitter_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.retry_policy.random.random", lambda: 0.0)
    with_jitter = RetryPolicy(base_delay=2.0, jitter=True)
    without = RetryPolicy(base_delay=2.0, jitter=False)
    assert without.compute_delay(0) == 2.0
    assert with_jitter.compute_delay(0) == 1.0
    _ = RetryPolicyFactory.for_llm()
    _ = RetryPolicyFactory.for_http()
    _ = RetryPolicyFactory.for_db()
