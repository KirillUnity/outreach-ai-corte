# Langfuse observability for LLM apps

Outreach AI Cortex (Day 9) self-hosts Langfuse v2 next to FastAPI. Traces are optional: empty keys disable the SDK so local/CI still boot.

## Why observability is critical for LLM apps

A FastAPI 500 and an Nginx access log tell you *that* a request failed. They do not tell you:

- which prompt version produced a spammy subject
- whether tokens (and dollars) came from the first call or the validation retry
- which LangGraph node burned 8 seconds
- whether `personalization_score` collapsed after a prompt tweak

LLM apps fail *quietly*: 200 OK with a polite, generic email that will never get a reply. Observability is how you see quality, cost, and latency as first-class signals — the same way APM shows SQL time.

### vs ordinary APM

| | APM (Datadog, Pyroscope, etc.) | LLM observability (Langfuse) |
|--|-------------------------------|------------------------------|
| Unit | HTTP request, SQL, CPU | **trace** → **span** (node) → **generation** (model call) |
| Payload | status, duration | prompts, completions, tokens, $ |
| Quality | error rate | scores, human thumbs, eval datasets |
| Sampling | traffic volume | `sample_rate` because generations are large |

## What we trace

1. **Generations** from `LLMClient.chat()` — `system` and `user` kept as separate fields so prompt diffs are obvious.
2. **Spans** around each graph node (`graph.py` wrapper). `decide` metadata: `decision`, `decision_reason`, `validation_errors`.
3. **Root traces** for `POST /agent/outreach` (`outreach_agent_{person_id}`) and `POST /persons/{id}/generate-email`.
4. **Scores** from `QualityScorer` (no extra LLM call): length, spam, personalization, CTA.
5. **Flush** after the run and on API shutdown so a short process does not drop the buffer.

`trace_id` is created in `OutreachAgentService.run()` / `EmailDraftService.generate_and_save()`, stored in a `ContextVar`, and passed into Langfuse spans/generations so children join the same tree. LangGraph also gets `CallbackHandler` when keys exist.

## Comparison

| Tool | Hosting | Fit for this repo |
|------|---------|-------------------|
| **Langfuse** | Cloud or Docker Compose | Chosen: OSS, Postgres-backed v2, LangChain/LangGraph callbacks, scores, self-host on 8 GB RAM |
| **Helicone** | Proxy in front of OpenAI | Excellent request logs; weaker graph/span model; another network hop |
| **Arize Phoenix** | Often local OTel | Strong evals; heavier local footprint than we want on Iris Xe / 8 GB |
| **LangSmith** | LangChain Cloud | Tight LangGraph UX; SaaS lock-in and extra vendor for a portfolio Docker demo |

We pin **langfuse/langfuse:2** (single Postgres) rather than Langfuse 3 (ClickHouse + workers) to stay under the Compose RAM cap.

## What we tested

- Unit: tracing no-op without keys; `CallbackHandler` is `None` when disabled; node exceptions mark span `ERROR`; scorer happy path / no name / spam words; cost and error-rate alerts.
- Manual (when Docker is up): generate-email → Traces; agent outreach → nested spans; Dashboard charts.

Priority metrics for this product, in order:

1. **Cost per successful draft** (`cost_usd` on generations + `AgentRun.cost_usd`)
2. **Validation / personalization scores** (catch prompt regressions without waiting for replies)
3. **p95 generation latency** (user-facing generate-email)
4. **Error rate on LLM + graph nodes** (retries vs hard fail)
5. **Token mix** input vs output (bloated RAG context vs verbose drafts)

## Using traces to improve prompts

- Filter traces where `personalization_score < 0.5` → the model ignored `first_name` / company. Fix the user template or add a validator retry (already exists for spam).
- Sort by `cost_usd` → over-long `raw_site_text` in RAG. Truncation already lives in `_safe_state` for Langfuse payloads; apply the same discipline to the prompt.
- Compare two `release` tags after a prompt edit (`LANGFUSE.release`).
- `sample_rate`: keep `1.0` in development; if ingest lags, sample production at `0.1` and always sample errors.

## Alerts

`AlertsService` logs a warning when a single run exceeds `$1` (tune the threshold) and when a window of runs has error share ≥ 10% (needs ≥ 5 runs). Without a cost alert, a retry loop on a paid model can empty an OpenAI budget overnight.

## Hardware note

No local models. Langfuse is CPU/RAM only (`mem_limit` 768m + 256m DB). API does **not** `depends_on: langfuse` so the product still starts if you skip the UI.
