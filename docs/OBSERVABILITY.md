# Observability

Three different signals. Do not collapse them into one dashboard container.

| Signal | Tool | What it is good for |
|--------|------|---------------------|
| Traces | Langfuse | One LLM or agent run: prompt shape, tokens, cost, node name |
| Metrics | `GET /metrics` | Request rate, latency, agent decision counts |
| Errors | Sentry (optional) | Exceptions after PII scrub |

No Grafana and no Prometheus server ship in this repo. On an 8 GB dev machine, and especially on a 1 GB VPS, those processes cost RAM the API needs. Scrape `/metrics` from a Prometheus that runs somewhere else.

## Langfuse

Keys stay empty in git. With `LANGFUSE_PUBLIC_KEY` or `LANGFUSE_SECRET_KEY` blank, tracing is a no-op and the API still starts.

| Variable | Prod note |
|----------|-----------|
| `LANGFUSE_HOST` | URL the API can reach, for example `http://langfuse:3000` on the Compose network |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | From the Langfuse UI, only in `.env` |
| `LANGFUSE_SAMPLE_RATE` | `0.1` in production (dev default in `.env.example` is `1.0`) |
| `LANGFUSE_ENABLED` | `false` on a 1 GB VPS |

Langfuse and its own Postgres are Compose profile `extra` ([docs/DEPLOY.md](DEPLOY.md)). Leave that profile off unless the host has spare RAM (Langfuse 512m plus its database 256m, on top of the API).

Do not log full prompts in application logs or in a metrics backend. A prompt contains the prospect's name, company research, and sometimes an email address. Langfuse already stores the generation; keep that store access-controlled and sampled.

## Sentry

`SENTRY_DSN` empty or `SENTRY_ENABLED=false` skips `sentry_sdk.init`. Nothing crashes.

When both are set, the app uses the FastAPI integration, `send_default_pii=false`, and `traces_sample_rate=0.1` when `DEBUG=false` (`1.0` when debug is on, so a local repro is not sampled away). `before_send` redacts email addresses and phone numbers.

Do not commit a real DSN.

## Metrics

`GET /metrics` is on the app root (not under `/api/v1`) and returns Prometheus text. Labels are method, route template, and status. `person_id` and email are not labels. Agent runs increment `agent_runs_total` with a decision bucket: `send`, `hold`, `reject`, `unknown`, or `other`.

`PROMETHEUS_ENABLED=false` returns HTTP 200 and the body `# prometheus metrics disabled`.

The production Compose file publishes the API on `127.0.0.1:8080` only. A Prometheus on another host needs a private path (SSH tunnel or a VPC), not a public Caddy route. Example job:

```yaml
scrape_configs:
  - job_name: outreach-api
    metrics_path: /metrics
    static_configs:
      - targets: ["127.0.0.1:8080"]
```

That snippet belongs in the scraper's `prometheus.yml`, which is not part of this Compose project.
