"""In-process Prometheus metrics. No Prometheus or Grafana server lives in Compose."""

from __future__ import annotations

import logging
import time
from typing import Any

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings

logger = logging.getLogger(__name__)

_DISABLED_BODY = b"# prometheus metrics disabled\n"
_DECISIONS = frozenset({"send", "hold", "reject", "unknown"})

registry = CollectorRegistry()

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests by method, route template, and status",
    ["method", "path", "status"],
    registry=registry,
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    registry=registry,
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)
AGENT_RUNS = Gauge(
    "agent_runs_total",
    "Completed outreach agent runs by decision bucket",
    ["decision"],
    registry=registry,
)


def path_label(scope: Scope) -> str:
    """Return the route template, never the raw path.

    Raw paths can contain ids or email addresses. Those must not become labels.
    """
    route: Any = scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str) and path and "@" not in path:
        return path
    return "unmatched"


def render_metrics() -> tuple[bytes, str]:
    """Serialize metrics, or a stable disabled body when the flag is off."""
    if not settings.prometheus_enabled:
        return _DISABLED_BODY, "text/plain; version=0.0.4; charset=utf-8"
    return generate_latest(registry), CONTENT_TYPE_LATEST


def note_agent_run(decision: str) -> None:
    """Count one finished agent run. The label is a decision bucket, not a person."""
    if not settings.prometheus_enabled:
        return
    try:
        bucket = decision if decision in _DECISIONS else "other"
        AGENT_RUNS.labels(decision=bucket).inc()
    except Exception:
        logger.exception("agent run metric skipped")


class PrometheusMiddleware:
    """Record request count and latency around the ASGI app."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not settings.prometheus_enabled:
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method") or "GET")
        status_code = 500
        start = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            path = path_label(scope)
            elapsed = time.perf_counter() - start
            HTTP_REQUESTS.labels(method=method, path=path, status=str(status_code)).inc()
            HTTP_LATENCY.labels(method=method, path=path).observe(elapsed)
