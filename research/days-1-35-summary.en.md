# Outreach AI Cortex — Days 1–35 canonical recap

Russian: [days-1-35-summary.ru.md](days-1-35-summary.ru.md). Historical slices stay published:
[1–27](days-1-27-summary.en.md), [1–20](days-1-20-summary.en.md), [1–12](days-1-12-summary.en.md),
and [1–8](days-1-8-summary.en.md). Do not treat those older files as deleted.

Honest cadence: days 1–17 were a daily build. Days 18–35 were **14 compressed prompts**
(`docs/day-prompts/`). **Days 25 and 30** were skipped in that pack and restored here.
**Day 33** is capture documentation, not an mp4 in git.

## Architecture

Python 3.12, FastAPI, async SQLAlchemy 2.0, PostgreSQL 16, ChromaDB, Neo4j,
React/Vite, Poetry, and Docker Compose. LLM and embedding production calls use cloud APIs only;
mock modes keep local development and CI deterministic. Postgres is the CRUD source of truth,
Chroma stores company RAG chunks, and Neo4j is a relationship/path index. Production on a VPS is
still Compose ([docs/DEPLOY.md](../docs/DEPLOY.md)): default api + postgres + frontend; Chroma is
profile `rag`; Neo4j and Langfuse are profile `extra`. Kubernetes is not the production path.
Locust is an optional Poetry group, not a container.

Counts: [docs/PROJECT_METRICS.md](../docs/PROJECT_METRICS.md). Demo path: [docs/DEMO.md](../docs/DEMO.md).
Ship changelog: [docs/RELEASE_NOTES.md](../docs/RELEASE_NOTES.md).

## Delivery timeline

- Days 1–12: platform bootstrap, company/person/email models, site research, cloud RAG and LLM
  wrappers, LangGraph outreach agent, observability, guardrails, analytics, and graph services.
- Days 13–17: React administration UI, warm-intro views, DNS deliverability, mailbox warmup
  emulator, and multi-source email candidates. Live SMTP recipient probing remains disabled.
- Days 18–20: mock-first company people search, Apollo adapter, sequence state machine, CRM
  adapters, n8n workflow drafts, and research notes.
- Day 21: `SEOArticle`, versioned article prompts, RAG-backed `ArticleGenerator`, CRUD/generate
  API, token/cost metadata, and draft-only generation.
- Day 22: idempotent mock/webhook publisher, scheduled queue, admin-protected due tick, hourly n8n
  workflow, and lightweight article list/generate/preview UI.
- Day 23: deterministic meta title/description, bounded keywords, safe same-company links, optional
  single LLM metadata call, and UI optimization controls (SEO fields were day 24 in the original
  35-day calendar).
- Day 25 (restored): content-marketing essay
  [research/content-marketing-b2b-seo.md](content-marketing-b2b-seo.md).
- Day 26: focused backend coverage, SMTP-disabled/duplicate/empty-result paths, Vitest UI states,
  and [testing guidance](../docs/TESTING.md).
- Day 27: GitHub Actions and GitLab CI with PostgreSQL 16, mock external modes, backend tests,
  frontend tests/build, and no deployment stage.
- Day 28: `docker-compose.prod.yml`, RAM table, Caddy on the host, backups, rollback notes.
- Day 29: Sentry, Prometheus `GET /metrics`, Langfuse production notes
  ([docs/OBSERVABILITY.md](../docs/OBSERVABILITY.md)).
- Day 30 (restored): read-only Locust against health and metrics
  ([docs/LOAD_TESTING.md](../docs/LOAD_TESTING.md)).
- Day 31: ARCHITECTURE, DEMO, PROMPTS catalog.
- Day 32: screenshot checklist and 5-minute video script
  ([docs/demo/SCREENSHOTS.md](../docs/demo/SCREENSHOTS.md),
  [VIDEO_SCRIPT.md](../docs/demo/VIDEO_SCRIPT.md)).
- Day 33: how to record and host the video
  ([docs/demo/CAPTURE.md](../docs/demo/CAPTURE.md)); binaries stay out of git.
- Day 34: interview answers ([docs/interview/ANSWERS.md](../docs/interview/ANSWERS.md)).
- Day 35: metrics, social drafts, release notes. Files only in the restore batch (no commit/push,
  no LinkedIn/Habr publish).

## Article lifecycle

`Company.raw_site_text → Chroma retrieval → versioned JSON prompt → validated SEOArticle(draft) →
operator review/optimize → scheduled → admin tick → mock or webhook publish`.

Generation never publishes automatically. Mock publishing uses `example.invalid`; webhook failures
mark the article failed. Internal links are restricted to the company domain and stored article
paths. The scheduler transition is status-based and repeat publishing is a no-op.

Outreach and SEO share that corpus. The editorial hold is the content analogue of
`AGENT_REQUIRE_HUMAN_APPROVAL`.

## Verification and operations

```bash
poetry run pytest -q
poetry run pytest --cov=app --cov-report=term-missing --cov-fail-under=0
cd frontend && npm ci && npm test && npm run build
docker compose exec api poetry run alembic upgrade head
poetry install --with load
poetry run locust -f loadtest/locustfile.py --host http://127.0.0.1:8080 --users 1 --spawn-rate 1 --headless -t 30s
```

CI uses Python 3.12, Node 20, and PostgreSQL 16. It does not start Chroma, Neo4j, Langfuse, Locust,
or the full Compose stack. Third-party credentials are not required in CI. Do not load-test
`POST /agent/outreach`.

Portfolio walkthrough: [DEMO.md](../docs/DEMO.md). Capture: [CAPTURE.md](../docs/demo/CAPTURE.md).
VPS: [DEPLOY.md](../docs/DEPLOY.md).

## Interview self-check

1. Why does an article belong to a company rather than a person?
2. Why is structured JSON safer than accepting raw model markdown?
3. How do RAG grounding and an editorial disclaimer reduce hallucination risk?
4. Why does generation stop at `draft`, and who approves publication?
5. How do status transitions and idempotency avoid duplicate scheduled publication?
6. Why is LLM SEO optimization off by default?
7. Why are metadata and internal-link lengths bounded? Why same-company links only?
8. Why is a focused coverage threshold safer than 80% across legacy code?
9. Why do CI jobs use mock modes and a real PostgreSQL service?
10. What differs between GitHub service containers and GitLab CI services?
11. Why is Locust not in Compose, and why must a swarm not call the agent?
12. What does p95 of `GET /health` not tell you about `POST /agent/outreach`?
13. Why is the demo video unlisted YouTube instead of git?
14. How do you describe “35 days” versus “14 compressed prompts” without lying?
15. Why never post API keys “for the demo,” and how do you measure a Habr/LinkedIn post without vanity metrics?
