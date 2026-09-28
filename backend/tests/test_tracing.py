"""TracingService with a fake Langfuse client — no Docker, no keys."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.config import LangfuseSettings, Settings
from app.services.tracing import TracingService, reset_tracing


class FakeSpan:
    def __init__(self) -> None:
        self.ended: list[dict] = []
        self.updates: list[dict] = []

    def end(self, **kwargs: object) -> None:
        self.ended.append(dict(kwargs))

    def update(self, **kwargs: object) -> None:
        self.updates.append(dict(kwargs))


class FakeLangfuse:
    def __init__(self) -> None:
        self.spans: list[tuple[dict, FakeSpan]] = []
        self.generations: list[dict] = []
        self.scores: list[dict] = []
        self.traces: list[dict] = []
        self.flushed = False

    def trace(self, **kwargs: object) -> SimpleNamespace:
        self.traces.append(dict(kwargs))
        return SimpleNamespace(id=kwargs.get("id"))

    def span(self, **kwargs: object) -> FakeSpan:
        handle = FakeSpan()
        self.spans.append((dict(kwargs), handle))
        return handle

    def generation(self, **kwargs: object) -> FakeSpan:
        self.generations.append(dict(kwargs))
        return FakeSpan()

    def score(self, **kwargs: object) -> None:
        self.scores.append(dict(kwargs))

    def flush(self) -> None:
        self.flushed = True


def _settings(*, enabled: bool = True, keys: bool = False) -> Settings:
    return Settings(
        langfuse=LangfuseSettings(
            enabled=enabled,
            public_key="pk-test" if keys else "",
            secret_key="sk-test" if keys else "",
            host="http://langfuse:3000",
        )
    )


def teardown_function() -> None:
    reset_tracing()


def test_tracing_disabled_when_no_keys() -> None:
    service = TracingService(_settings(enabled=True, keys=False))
    assert service.enabled is False
    assert service.get_callback_handler("outreach") is None


def test_get_callback_handler_returns_none_when_disabled() -> None:
    service = TracingService(_settings(enabled=False, keys=True), client=FakeLangfuse())
    assert service.enabled is False
    assert service.get_callback_handler("outreach") is None


def test_trace_node_with_error_marks_span() -> None:
    fake = FakeLangfuse()
    service = TracingService(_settings(enabled=True, keys=True), client=fake)
    with pytest.raises(RuntimeError, match="boom"):
        with service.trace_node("decide", {"iteration": 1}):
            raise RuntimeError("boom")
    assert fake.spans
    ended = fake.spans[0][1].ended
    assert ended
    assert ended[0].get("level") == "ERROR"
    assert "boom" in str(ended[0].get("status_message"))


def test_flush_is_noop_when_disabled() -> None:
    service = TracingService(_settings(enabled=True, keys=False))
    service.flush()
