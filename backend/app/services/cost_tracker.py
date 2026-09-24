"""Rough USD cost estimates for cloud chat and embedding calls."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# USD per 1M tokens. Enough for a pet-project ledger — not a billing system.
_CHAT_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4o": (2.50, 10.00),
}


@dataclass(frozen=True)
class CostRecord:
    """One LLM (or embedding) call."""

    model: str
    tokens_input: int
    tokens_output: int
    estimated_cost_usd: float


class CostTracker:
    """Accumulate token spend for a single request (or a test)."""

    def __init__(self) -> None:
        self.records: list[CostRecord] = []

    def estimate_chat(self, model: str, tokens_input: int, tokens_output: int) -> float:
        """Return USD for a chat completion using a small static price table."""
        input_rate, output_rate = _CHAT_PRICES.get(model, (0.15, 0.60))
        cost = (tokens_input / 1_000_000) * input_rate + (tokens_output / 1_000_000) * output_rate
        return round(cost, 8)

    def log_chat(self, model: str, tokens_input: int, tokens_output: int) -> CostRecord:
        """Store a chat call and log it. Safe to call from mock mode (cost is ~0)."""
        cost = self.estimate_chat(model, tokens_input, tokens_output)
        record = CostRecord(
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            estimated_cost_usd=cost,
        )
        self.records.append(record)
        logger.info(
            "llm cost model=%s in=%s out=%s usd=%.8f",
            model,
            tokens_input,
            tokens_output,
            cost,
        )
        return record

    @property
    def total_usd(self) -> float:
        """Sum of recorded chat costs."""
        return round(sum(record.estimated_cost_usd for record in self.records), 8)
