# Load testing (Locust, RAM-safe)

Locust is an **optional Poetry group** (`load`). It is not a Compose service. Do not add Locust, Grafana, or Prometheus servers to `docker-compose.yml` or `docker-compose.prod.yml`. The 8 GB laptop and a 1 GB VPS cannot host a swarm next to Postgres, the API, and the UI.

## Install and run

Against a local API already listening on loopback:

```bash
poetry install --with load
poetry run locust -f loadtest/locustfile.py --host http://127.0.0.1:8080 --users 1 --spawn-rate 1
```

Headless (no extra UI process):

```bash
poetry run locust -f loadtest/locustfile.py --host http://127.0.0.1:8080 --users 1 --spawn-rate 1 --headless -t 30s
```

`ReadOnlyUser` waits 1–3 seconds between tasks. Tasks are **GET `/api/v1/health`** and **GET `/metrics` only**. Never point this file at `POST /api/v1/agent/outreach`, article generate, company research, or other LLM/RAG writes: that spends cloud tokens, fills Chroma, and can OOM the API container (`mem_limit` 512m).

Never suggest hundreds of users on this laptop. `--users 1 --spawn-rate 1` is the documented default.

## Why this is not in CI

CI already runs pytest against PostgreSQL 16 in mock LLM/RAG modes. A Locust job would need a long-lived API, would add a second Python extra, and would not prove agent latency. Flaky wall-clock numbers on shared runners are vanity. Keep Locust as a manual check on a machine you control.

## 1 GB VPS warning

Production Compose default is about 1.1 GB of container limits before the OS ([DEPLOY.md](DEPLOY.md)). Adding a Locust master, workers, Grafana, or Prometheus on that box will steal RAM from Postgres. If you scrape metrics, scrape from the host (`127.0.0.1:8080/metrics`) without another container. Do not enable `--profile extra` (Neo4j, Langfuse) during even a one-user Locust run on 1 GB.

## SLOs worth watching

| Signal | What it tells you | What it does not |
|--------|-------------------|------------------|
| p95 of `GET /api/v1/health` | Event loop + Postgres (+ Chroma if present) | Agent graph, LLM, RAG retrieve, guardrails |
| p95 of `GET /metrics` | Scrape handler; used as container health in prod | Business correctness |
| p95 of `POST /agent/outreach` | Real user-facing latency (measure with **one** curl, not a swarm) | Must not be load-tested here |
| Error rate on health | Process down or Chroma missing (prod default profile) | Token cost |

p95 of `/health` staying under a few hundred milliseconds is a liveness SLO. It says nothing about `generate_email` or Chroma HNSW under write load. Quote agent SLOs from Langfuse traces or a single manual run, not from this Locust file.

## Self-check

- Why not Locust in Compose? RAM. The load tool is not a product dependency.
- Why not POST outreach in a swarm? Cost, rate limits, and 512m API memory.
- What does p95 of `/health` not tell you about the agent? Node time, LLM latency, RAG quality, hold/send mix.
