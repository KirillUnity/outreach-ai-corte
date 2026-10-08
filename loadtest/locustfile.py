"""Read-only Locust tasks for a tiny RAM budget.

Hit only GET /api/v1/health and GET /metrics. Do not swarm POST /agent/outreach
or any LLM/RAG write path. Suggested local run: --users 1 --spawn-rate 1.
"""

from locust import HttpUser, between, task


class ReadOnlyUser(HttpUser):
    """One slow user against liveness and scrape endpoints."""

    wait_time = between(1, 3)

    @task(2)
    def health(self) -> None:
        """PostgreSQL/Chroma/LLM config probe. No token spend."""
        self.client.get("/api/v1/health")

    @task(1)
    def metrics(self) -> None:
        """Prometheus text. Does not require Chroma."""
        self.client.get("/metrics")
