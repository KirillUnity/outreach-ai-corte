"""Prometheus text endpoint. Counters live in the metrics service."""

from fastapi import APIRouter
from fastapi.responses import Response

from app.services.metrics import render_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics", summary="Prometheus metrics")
async def metrics() -> Response:
    """Return scrape text. Disabled mode is a stable 200, not a stack trace."""
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)
