"""Deterministic fake inbox network for warmup simulation."""

from __future__ import annotations

import random


class PeerNetwork:
    """Fixed set of peer addresses (`peerN@warmup-network.local`)."""

    def __init__(self, size: int = 20, seed: int = 42) -> None:
        self.size = size
        self._rng = random.Random(seed)
        self.peers = [f"peer{i}@warmup-network.local" for i in range(1, size + 1)]

    def get_random_peers(self, count: int, exclude_domain: str | None = None) -> list[str]:
        """Return `count` peers, optionally skipping a sending domain."""
        pool = self.peers
        if exclude_domain:
            needle = exclude_domain.lower().lstrip("@")
            pool = [email for email in pool if not email.lower().endswith(f"@{needle}")]
        if not pool:
            return []
        n = min(count, len(pool))
        return self._rng.sample(pool, n)
