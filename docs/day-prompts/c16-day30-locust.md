# Day 30 (restored) — Locust, RAM-safe

Skipped in the 14-prompt pack. Restored without putting Locust in Compose.

```
ROLE
Optional Poetry group `load`. locustfile hits GET /api/v1/health and GET /metrics only.
Wait 1–3s. Document --users 1 --spawn-rate 1. Never hundreds of users on the 8 GB laptop.
docs/LOAD_TESTING.md: how to run at http://127.0.0.1:8080; not in CI; 1 GB VPS warning;
SLOs (health latency vs agent). Tiny pytest without a live server.

DO NOT
Add Locust/Grafana/Prometheus to Compose. Do not load-test POST /agent/outreach or LLM/RAG writes.

SELF-CHECK
Why not Locust in Compose? Why not POST outreach in a swarm? What does p95 of /health not tell you about the agent?
```
