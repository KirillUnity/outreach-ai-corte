"""Heuristic guardrails — no cloud PII API, no local NER."""

from __future__ import annotations

import asyncio
import time

from app.services.guardrails.base import BaseGuardrail, GuardrailResult
from app.services.guardrails.content_policy import ContentPolicyGuardrail
from app.services.guardrails.hallucination import HallucinationGuardrail
from app.services.guardrails.pii import PIIGuardrail
from app.services.guardrails.pipeline import GuardrailPipeline, build_default_pipeline
from app.services.guardrails.structure import StructureGuardrail


def _words(n: int, extra: str = "") -> str:
    return f"{extra} " + " ".join(["word"] * n)


async def test_hallucination_guardrail_detects_unknown_entity() -> None:
    rail = HallucinationGuardrail()
    result = await rail.check(
        "Jane, our Zorpify rollout at Acme is ready.",
        {"person": {"first_name": "Jane"}, "company": {"name": "Acme"}, "rag_context": "Acme sells widgets"},
    )
    assert "zorpify" in result.metadata.get("unknown_entities", [])


async def test_content_policy_blocks_critical_words() -> None:
    rail = ContentPolicyGuardrail()
    result = await rail.check("People tell you to kill yourself in this industry.")
    assert result.passed is False
    assert result.severity == "critical"


async def test_pii_guardrail_detects_phone() -> None:
    rail = PIIGuardrail()
    result = await rail.check("Call me at +1-415-555-0100 tomorrow.")
    assert result.passed is False
    assert result.metadata.get("pii_types", {}).get("phone")


async def test_pii_guardrail_allows_sender_email() -> None:
    rail = PIIGuardrail()
    result = await rail.check(
        "Reply to  kirill@aicortex.dev when you can.",
        {"sender_email": "kirill@aicortex.dev"},
    )
    assert result.passed is True
    assert result.metadata.get("pii_types") == {}


async def test_structure_guardrail_missing_cta() -> None:
    rail = StructureGuardrail()
    body = _words(80, extra="Jane, I wanted to share an observation about your billing API.")
    result = await rail.check(body, {"person": {"first_name": "Jane"}})
    assert "cta" in result.metadata.get("missing_sections", [])
    assert result.passed is False


async def test_pipeline_runs_parallel() -> None:
    class Slow(BaseGuardrail):
        name = "slow"

        async def check(self, content: str, context=None) -> GuardrailResult:
            await asyncio.sleep(0.05)
            return GuardrailResult(passed=True, name=self.name)

    pipe = GuardrailPipeline([Slow(), Slow()])
    started = time.perf_counter()
    passed, results = await pipe.run_all("hello")
    elapsed = time.perf_counter() - started
    assert passed is True
    assert len(results) == 2
    assert elapsed < 0.15


async def test_pipeline_blocks_on_critical() -> None:
    pipe = build_default_pipeline()
    passed, results = await pipe.run_all("kill yourself now")
    assert passed is False
    blockers = pipe.get_blockers(results)
    assert any(item.name == "content_policy" for item in blockers)
    summary = pipe.summarize(results)
    assert summary["failed"] >= 1
