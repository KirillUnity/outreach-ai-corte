"""Read-only aggregates for cost, quality, guardrails, and agent decisions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.models.email_draft import EmailDraft


class AnalyticsService:
    """SQL aggregations over AgentRun + EmailDraft JSONB metadata."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _since(self, days: int) -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=days)

    async def costs_summary(self, days: int = 7) -> dict[str, Any]:
        since = self._since(days)
        result = await self.db.execute(
            select(
                func.count(AgentRun.id).label("total_runs"),
                func.sum(AgentRun.cost_usd).label("total_cost"),
                func.avg(AgentRun.cost_usd).label("avg_cost"),
                func.sum(AgentRun.tokens_input).label("total_input_tokens"),
                func.sum(AgentRun.tokens_output).label("total_output_tokens"),
            ).where(AgentRun.created_at >= since)
        )
        row = result.one()
        return {
            "days": days,
            "total_runs": int(row.total_runs or 0),
            "total_cost_usd": float(row.total_cost or 0.0),
            "avg_cost_usd": float(row.avg_cost or 0.0),
            "total_input_tokens": int(row.total_input_tokens or 0),
            "total_output_tokens": int(row.total_output_tokens or 0),
        }

    async def costs_by_model(self, days: int = 7) -> dict[str, Any]:
        since = self._since(days)
        model_col = EmailDraft.generation_context["model"].astext
        cost_col = cast(EmailDraft.generation_context["estimated_cost_usd"].astext, Float)
        result = await self.db.execute(
            select(
                model_col.label("model"),
                func.count().label("drafts"),
                func.sum(cost_col).label("total_cost"),
            )
            .where(EmailDraft.created_at >= since)
            .group_by(model_col)
        )
        items = []
        for row in result.all():
            items.append(
                {
                    "model": row.model or "unknown",
                    "drafts": int(row.drafts or 0),
                    "total_cost_usd": float(row.total_cost or 0.0),
                }
            )
        return {"days": days, "items": items}

    async def quality_scores(self, days: int = 7) -> dict[str, Any]:
        since = self._since(days)
        scores = EmailDraft.generation_context["quality_scores"]
        result = await self.db.execute(
            select(
                func.avg(cast(scores["length_score"].astext, Float)).label("length_score"),
                func.avg(cast(scores["spam_score"].astext, Float)).label("spam_score"),
                func.avg(cast(scores["personalization_score"].astext, Float)).label(
                    "personalization_score"
                ),
                func.avg(cast(scores["cta_score"].astext, Float)).label("cta_score"),
                func.count().label("n"),
            ).where(EmailDraft.created_at >= since)
        )
        row = result.one()
        return {
            "days": days,
            "n": int(row.n or 0),
            "length_score": float(row.length_score or 0.0),
            "spam_score": float(row.spam_score or 0.0),
            "personalization_score": float(row.personalization_score or 0.0),
            "cta_score": float(row.cta_score or 0.0),
        }

    async def guardrail_failures(self, days: int = 7) -> dict[str, Any]:
        since = self._since(days)
        result = await self.db.execute(
            select(EmailDraft.guardrail_results).where(EmailDraft.created_at >= since)
        )
        counts: dict[str, int] = {}
        for payload in result.scalars().all():
            items = payload if isinstance(payload, list) else []
            for item in items:
                if isinstance(item, dict) and not item.get("passed"):
                    name = str(item.get("name") or "unknown")
                    counts[name] = counts.get(name, 0) + 1
        top = sorted(counts.items(), key=lambda pair: pair[1], reverse=True)
        return {
            "days": days,
            "items": [{"name": name, "failures": n} for name, n in top],
        }

    async def agent_decisions(self, days: int = 7) -> dict[str, Any]:
        since = self._since(days)
        result = await self.db.execute(
            select(AgentRun.decision, func.count().label("n"))
            .where(AgentRun.created_at >= since)
            .group_by(AgentRun.decision)
        )
        items = [{"decision": row.decision, "count": int(row.n)} for row in result.all()]
        return {"days": days, "items": items}
