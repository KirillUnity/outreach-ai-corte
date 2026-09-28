# Days 1–10 summary

Portfolio backend for AI-assisted B2B outreach. Stack: FastAPI, async SQLAlchemy, PostgreSQL 16, ChromaDB, LangGraph, Langfuse v2, cloud LLM only.

## What shipped

| Day | Theme |
|-----|--------|
| 1 | Compose + FastAPI + health |
| 2 | Alembic, Company model |
| 3 | Person, EmailDraft, DomainHealth CRUD |
| 4 | Site parser / research |
| 5 | LinkedIn mock/real |
| 6 | RAG / Chroma |
| 7 | Email generation + validator |
| 8 | LangGraph agent |
| 9 | Langfuse tracing, scores, alerts |
| 10 | Guardrails, retry policy, analytics, prompt catalog |

## Metrics (code, not a live coverage run)

- HTTP: health, companies, persons, drafts, deliverability, agent, **analytics** (`/api/v1/analytics/...`)
- ORM: 5 core tables + `agent_runs` + `email_drafts.guardrail_results`
- Tests: parser, CRUD-adjacent, RAG, LLM, agent edges/nodes/graph, tracing, scoring, **guardrails, retry, analytics**
- Coverage: aim **70%+ on `app/services`**; 100% of the repo is not a goal (Compose, Alembic env, vendor SDK wrappers)

## Next (days 11–20, not in this commit)

Neo4j relationship graph, real SMTP/deliverability, React console, CRM integrations.

## Run Day 10

```bash
docker compose up -d --build
docker compose exec api poetry run alembic upgrade head
docker compose exec api poetry run pytest tests/test_guardrails.py tests/test_retry_policy.py tests/test_analytics.py -v
```
