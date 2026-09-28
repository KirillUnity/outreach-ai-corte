"""Cheap post-run guards — log warnings, do not page anyone yet."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class AlertsService:
    """Threshold checks after an agent run. Without these, a retry loop can burn budget overnight."""

    def check_cost_threshold(self, cost_usd: float, threshold: float = 1.0) -> bool:
        """True when this run (or the session total) crossed the USD cap."""
        if cost_usd >= threshold:
            logger.warning("alert cost_usd=%.4f threshold=%.4f", cost_usd, threshold)
            return True
        return False

    def check_error_rate(self, errors: int, total_runs: int, threshold: float = 0.1) -> bool:
        """True when recent error share is above threshold (need a few runs first)."""
        if total_runs < 5:
            return False
        rate = errors / total_runs
        if rate >= threshold:
            logger.warning("alert error_rate=%.3f threshold=%.3f n=%s", rate, threshold, total_runs)
            return True
        return False
