"""Weighted prompt variants for cheap online experiments (in-process stats)."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class _Stats:
    trials: int = 0
    successes: int = 0
    score_sum: float = 0.0


class PromptABTester:
    """Pick a labeled variant; accumulate success/score for later comparison."""

    def __init__(self, variants: list[str], weights: list[float] | None = None) -> None:
        if not variants:
            raise ValueError("need at least one prompt variant")
        self.variants = list(variants)
        if weights is None:
            self.weights = [1.0] * len(self.variants)
        else:
            if len(weights) != len(self.variants):
                raise ValueError("weights must match variants")
            self.weights = list(weights)
        self._stats: dict[str, _Stats] = {name: _Stats() for name in self.variants}

    def pick_variant(self) -> str:
        return random.choices(self.variants, weights=self.weights, k=1)[0]

    def log_result(self, variant: str, success: bool, score: float) -> None:
        row = self._stats.setdefault(variant, _Stats())
        row.trials += 1
        if success:
            row.successes += 1
        row.score_sum += float(score)

    def snapshot(self) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for name, row in self._stats.items():
            avg = row.score_sum / row.trials if row.trials else 0.0
            rate = row.successes / row.trials if row.trials else 0.0
            out[name] = {"trials": float(row.trials), "success_rate": rate, "avg_score": avg}
        return out


_DEFAULT_SUFFIXES: dict[str, str] = {
    "v1_default": "",
    "v1_direct_cta": (
        "\nPrefer a single concrete CTA with a 15-minute window. Do not stack questions."
    ),
}


def default_prompt_ab() -> PromptABTester:
    return PromptABTester(list(_DEFAULT_SUFFIXES.keys()))


def suffix_for(variant: str) -> str:
    return _DEFAULT_SUFFIXES.get(variant, "")
