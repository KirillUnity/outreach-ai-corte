"""Langfuse tracing with a hard no-op path when keys are missing."""

from __future__ import annotations

import logging
import random
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

from app.core.config import Settings, settings as default_settings

logger = logging.getLogger(__name__)

_current_trace_id: ContextVar[str | None] = ContextVar("langfuse_trace_id", default=None)


def _safe_state(state: dict[str, Any] | None) -> dict[str, Any]:
    """Drop huge fields so Langfuse payloads stay small."""
    if not state:
        return {}
    out: dict[str, Any] = {}
    for key, value in state.items():
        if key in {"company_data"} and isinstance(value, dict):
            slim = dict(value)
            text = slim.get("raw_site_text")
            if isinstance(text, str) and len(text) > 400:
                slim["raw_site_text"] = text[:400] + "…"
            out[key] = slim
        else:
            out[key] = str(value) if not isinstance(value, str | int | float | bool | list | dict | type(None)) else value
    return out


class _NoopHandle:
    """Stand-in span/generation when tracing is off."""

    def update(self, **_kwargs: Any) -> None:
        return None

    def set_output(self, _output: Any) -> None:
        return None

    def set_metadata(self, **_kwargs: Any) -> None:
        return None

    def mark_error(self, _message: str) -> None:
        return None


class TracingService:
    """Create traces/spans/generations. Safe to construct in tests with a fake client."""

    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or default_settings
        self._client = client
        cfg = self.settings.langfuse
        keys_ok = bool(cfg.public_key and cfg.secret_key)
        # Injected client (tests) does not need real keys.
        if client is not None:
            self.enabled = bool(cfg.enabled)
        else:
            self.enabled = bool(cfg.enabled and keys_ok)
            if self.enabled:
                self._client = self._build_client()
        if not self.enabled:
            logger.info("langfuse tracing disabled (no keys or LANGFUSE_ENABLED=false)")

    def _build_client(self) -> Any:
        from langfuse import Langfuse

        cfg = self.settings.langfuse
        return Langfuse(
            public_key=cfg.public_key,
            secret_key=cfg.secret_key,
            host=cfg.host,
        )

    def _sampled(self) -> bool:
        rate = float(self.settings.langfuse.sample_rate)
        if rate >= 1.0:
            return True
        if rate <= 0.0:
            return False
        return random.random() < rate

    def bind_trace(self, trace_id: str) -> Any:
        """Attach this request's trace_id to the context (scores/spans join it)."""
        return _current_trace_id.set(trace_id)

    def unbind_trace(self, token: Any) -> None:
        _current_trace_id.reset(token)

    def current_trace_id(self) -> str | None:
        return _current_trace_id.get()

    def start_trace(self, name: str, metadata: dict[str, Any] | None = None) -> str:
        """Open a root trace and bind it. Returns the trace_id (always, even if no-op)."""
        trace_id = str(uuid4())
        if self.enabled and self._sampled() and self._client is not None:
            cfg = self.settings.langfuse
            self._client.trace(
                id=trace_id,
                name=name,
                metadata=metadata or {},
                release=cfg.release,
                tags=[cfg.environment],
            )
        return trace_id

    def get_callback_handler(
        self,
        trace_name: str,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Any | None:
        """LangChain/LangGraph CallbackHandler, or None when tracing is off."""
        if not self.enabled or self._client is None:
            return None
        try:
            from langfuse.callback import CallbackHandler
        except ImportError:
            logger.warning("langfuse.callback.CallbackHandler unavailable")
            return None
        cfg = self.settings.langfuse
        return CallbackHandler(
            public_key=cfg.public_key,
            secret_key=cfg.secret_key,
            host=cfg.host,
            session_id=session_id,
            trace_name=trace_name,
            metadata=metadata or {},
        )

    @contextmanager
    def trace_node(self, node_name: str, state: dict[str, Any] | None = None) -> Iterator[Any]:
        """Span around a graph node. Marks ERROR if the body raises."""
        handle = _NoopHandle()
        span = None
        if self.enabled and self._client is not None:
            try:
                trace_id = self.current_trace_id()
                if trace_id:
                    span = self._client.span(
                        trace_id=trace_id,
                        name=node_name,
                        input=_safe_state(state),
                    )
                    handle = _LiveSpan(span)
                else:
                    span = self._client.span(name=node_name, input=_safe_state(state))
                    handle = _LiveSpan(span)
            except Exception:
                logger.exception("langfuse span start failed node=%s", node_name)
                span = None
        try:
            yield handle
        except Exception as exc:
            handle.mark_error(str(exc))
            raise
        else:
            if getattr(handle, "output", None) is None and span is not None:
                handle.set_output({})

    @contextmanager
    def trace_generation(
        self,
        name: str,
        model: str,
        input_payload: dict[str, Any],
    ) -> Iterator[Any]:
        """Generation object for a single LLM call (system + user kept separate)."""
        handle = _NoopHandle()
        if self.enabled and self._client is not None:
            try:
                kwargs: dict[str, Any] = {
                    "name": name,
                    "model": model,
                    "input": input_payload,
                }
                trace_id = self.current_trace_id()
                if trace_id:
                    kwargs["trace_id"] = trace_id
                gen = self._client.generation(**kwargs)
                handle = _LiveGeneration(gen)
            except Exception:
                logger.exception("langfuse generation start failed")
        try:
            yield handle
        except Exception as exc:
            handle.mark_error(str(exc))
            raise

    def log_llm_call(
        self,
        operation: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        duration_ms: float,
    ) -> None:
        """Extra generation metrics when we already have token counts."""
        if not self.enabled or self._client is None:
            return
        try:
            kwargs: dict[str, Any] = {
                "name": operation,
                "model": model,
                "usage": {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": input_tokens + output_tokens,
                },
                "metadata": {"cost_usd": cost_usd, "duration_ms": duration_ms},
            }
            trace_id = self.current_trace_id()
            if trace_id:
                kwargs["trace_id"] = trace_id
            gen = self._client.generation(**kwargs)
            if hasattr(gen, "end"):
                gen.end()
        except Exception:
            logger.exception("langfuse log_llm_call failed")

    def log_scores(self, draft_id: str, scores: dict[str, float], comment: str | None = None) -> None:
        """Attach numeric quality scores to the current (or given) trace."""
        if not self.enabled or self._client is None:
            return
        trace_id = self.current_trace_id()
        for name, value in scores.items():
            try:
                payload: dict[str, Any] = {
                    "name": name,
                    "value": float(value),
                    "comment": comment or f"draft_id={draft_id}",
                }
                if trace_id:
                    payload["trace_id"] = trace_id
                self._client.score(**payload)
            except Exception:
                logger.exception("langfuse score failed name=%s", name)

    def flush(self) -> None:
        """Push buffered events. Without this a short process can drop the last traces."""
        if self._client is None or not hasattr(self._client, "flush"):
            return
        try:
            self._client.flush()
        except Exception:
            logger.exception("langfuse flush failed")


class _LiveSpan:
    def __init__(self, span: Any) -> None:
        self._span = span
        self.output: Any = None
        self._metadata: dict[str, Any] = {}

    def update(self, **kwargs: Any) -> None:
        if hasattr(self._span, "update"):
            self._span.update(**kwargs)

    def set_output(self, output: Any) -> None:
        self.output = output
        self._end(output=output)

    def set_metadata(self, **kwargs: Any) -> None:
        self._metadata.update(kwargs)
        if hasattr(self._span, "update"):
            self._span.update(metadata=self._metadata)

    def mark_error(self, message: str) -> None:
        self._end(level="ERROR", status_message=message)

    def _end(self, **kwargs: Any) -> None:
        if self._metadata and "metadata" not in kwargs:
            kwargs["metadata"] = self._metadata
        if hasattr(self._span, "end"):
            self._span.end(**kwargs)
        elif hasattr(self._span, "update"):
            self._span.update(**kwargs)


class _LiveGeneration:
    def __init__(self, generation: Any) -> None:
        self._generation = generation

    def update(self, **kwargs: Any) -> None:
        if hasattr(self._generation, "end"):
            self._generation.end(**kwargs)
        elif hasattr(self._generation, "update"):
            self._generation.update(**kwargs)

    def mark_error(self, message: str) -> None:
        self.update(level="ERROR", status_message=message)

    def set_output(self, output: Any) -> None:
        self.update(output=output)

    def set_metadata(self, **kwargs: Any) -> None:
        self.update(metadata=kwargs)


def get_tracing() -> TracingService:
    """Process-wide tracer (same idea as get_settings)."""
    return _tracing_singleton()


def _tracing_singleton() -> TracingService:
    global _TRACING
    if _TRACING is None:
        _TRACING = TracingService(default_settings)
    return _TRACING


_TRACING: TracingService | None = None


def reset_tracing() -> None:
    """Tests: drop the cached tracer."""
    global _TRACING
    _TRACING = None
