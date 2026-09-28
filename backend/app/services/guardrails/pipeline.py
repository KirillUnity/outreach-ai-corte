"""Run every guardrail; warnings never block, errors/critical do."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.services.guardrails.base import BaseGuardrail, GuardrailResult
from app.services.guardrails.content_policy import ContentPolicyGuardrail
from app.services.guardrails.hallucination import HallucinationGuardrail
from app.services.guardrails.pii import PIIGuardrail
from app.services.guardrails.structure import StructureGuardrail

logger = logging.getLogger(__name__)

_BLOCKING = frozenset({"error", "critical"})


class GuardrailPipeline:
    """Fan-out checks. One crashed rail becomes an error result, not a 500."""

    def __init__(self, guardrails: list[BaseGuardrail]) -> None:
        self.guardrails = guardrails

    async def run_all(
        self, content: str, context: dict[str, Any] | None = None
    ) -> tuple[bool, list[GuardrailResult]]:
        ctx = context or {}
        raw = await asyncio.gather(
            *(self._safe_check(rail, content, ctx) for rail in self.guardrails),
            return_exceptions=False,
        )
        results = list(raw)
        all_passed = not any((not item.passed) and item.severity in _BLOCKING for item in results)
        return all_passed, results

    async def _safe_check(
        self, rail: BaseGuardrail, content: str, context: dict[str, Any]
    ) -> GuardrailResult:
        try:
            result = await rail.check(content, context)
            if not result.name:
                result.name = rail.name
            return result
        except Exception as exc:
            logger.exception("guardrail crashed name=%s", rail.name)
            return GuardrailResult(
                passed=False,
                reason=str(exc),
                severity="error",
                metadata={"exception": type(exc).__name__},
                name=rail.name,
            )

    def get_blockers(self, results: list[GuardrailResult]) -> list[GuardrailResult]:
        return [item for item in results if (not item.passed) and item.severity in _BLOCKING]

    def summarize(self, results: list[GuardrailResult]) -> dict[str, Any]:
        by_severity: dict[str, int] = {}
        failed = 0
        for item in results:
            by_severity[item.severity] = by_severity.get(item.severity, 0) + 1
            if not item.passed:
                failed += 1
        return {
            "total": len(results),
            "passed": len(results) - failed,
            "failed": failed,
            "by_severity": by_severity,
        }


def build_default_pipeline() -> GuardrailPipeline:
    """Production default set — regex/heuristics only, no local models."""
    return GuardrailPipeline(
        [
            HallucinationGuardrail(),
            ContentPolicyGuardrail(),
            PIIGuardrail(),
            StructureGuardrail(),
        ]
    )


def results_as_dicts(results: list[GuardrailResult]) -> list[dict[str, Any]]:
    """JSON-safe payload for EmailDraft / LangGraph state."""
    return [
        {
            "name": item.name,
            "passed": item.passed,
            "reason": item.reason,
            "severity": item.severity,
            "metadata": item.metadata,
        }
        for item in results
    ]
