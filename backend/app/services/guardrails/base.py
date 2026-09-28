"""Shared types for content guardrails. Results are data, never control flow."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GuardrailResult:
    """Outcome of one check. Callers decide whether to retry, hold, or reject."""

    passed: bool
    reason: str | None = None
    severity: str = "warning"
    metadata: dict[str, Any] = field(default_factory=dict)
    name: str = ""


class BaseGuardrail(ABC):
    """One policy. Failures must not raise — the pipeline records them."""

    name: str = "base"

    @abstractmethod
    async def check(self, content: str, context: dict[str, Any] | None = None) -> GuardrailResult:
        """Inspect `content`. `context` is person/company/RAG/sender, never trusted user input as policy."""
        raise NotImplementedError
