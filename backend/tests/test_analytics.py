"""AnalyticsService with a fake session — no live Postgres required."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.services.analytics_service import AnalyticsService


def _session_one(row: SimpleNamespace) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    result.one.return_value = row
    db.execute.return_value = result
    return db


async def test_costs_summary_empty() -> None:
    db = _session_one(
        SimpleNamespace(
            total_runs=0,
            total_cost=None,
            avg_cost=None,
            total_input_tokens=None,
            total_output_tokens=None,
        )
    )
    out = await AnalyticsService(db).costs_summary(days=7)
    assert out["total_runs"] == 0
    assert out["total_cost_usd"] == 0.0


async def test_costs_summary_with_data() -> None:
    db = _session_one(
        SimpleNamespace(
            total_runs=4,
            total_cost=1.25,
            avg_cost=0.3125,
            total_input_tokens=800,
            total_output_tokens=200,
        )
    )
    out = await AnalyticsService(db).costs_summary(days=7)
    assert out["total_runs"] == 4
    assert out["total_cost_usd"] == 1.25
    assert out["total_input_tokens"] == 800


async def test_quality_scores_aggregation() -> None:
    db = _session_one(
        SimpleNamespace(
            n=3,
            length_score=0.8,
            spam_score=1.0,
            personalization_score=0.5,
            cta_score=1.0,
        )
    )
    out = await AnalyticsService(db).quality_scores(days=7)
    assert out["n"] == 3
    assert out["length_score"] == 0.8
    assert out["personalization_score"] == 0.5
