# Outreach AI Cortex — Days 1–27 canonical recap

Russian: [days-1-27-summary.ru.md](days-1-27-summary.ru.md). Historical slices:
[1–20](days-1-20-summary.en.md), [1–12](days-1-12-summary.en.md), and
[1–8](days-1-8-summary.en.md).

## Architecture

Python 3.12, FastAPI, async SQLAlchemy 2.0, PostgreSQL 16, ChromaDB, Neo4j,
React/Vite, Poetry, and Docker Compose. LLM and embedding production calls use cloud APIs only;
mock modes keep local development and CI deterministic. Postgres is the CRUD source of truth,
Chroma stores company RAG chunks, and Neo4j is a relationship/path index.

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
  single LLM metadata call, and UI optimization controls.
- Day 26: focused backend coverage, SMTP-disabled/duplicate/empty-result paths, Vitest UI states,
  and [testing guidance](../docs/TESTING.md).
- Day 27: GitHub Actions and GitLab CI with PostgreSQL 16, mock external modes, backend tests,
  frontend tests/build, and no deployment stage.

## Article lifecycle

`Company.raw_site_text → Chroma retrieval → versioned JSON prompt → validated SEOArticle(draft) →
operator review/optimize → scheduled → admin tick → mock or webhook publish`.

Generation never publishes automatically. Mock publishing uses `example.invalid`; webhook failures
mark the article failed. Internal links are restricted to the company domain and stored article
paths. The scheduler transition is status-based and repeat publishing is a no-op.

## Verification and operations

```bash
poetry run pytest -q
poetry run pytest --cov=app --cov-report=term-missing --cov-fail-under=0
cd frontend && npm ci && npm test && npm run build
docker compose exec api poetry run alembic upgrade head
```

CI uses Python 3.12, Node 20, and PostgreSQL 16. It does not start Chroma, Neo4j, Langfuse, or the
full Compose stack. Third-party credentials are not required in CI.

## Interview self-check

1. Why does an article belong to a company rather than a person?
2. Why is structured JSON safer than accepting raw model markdown?
3. How do RAG grounding and an editorial disclaimer reduce hallucination risk?
4. Why does generation stop at `draft`, and who approves publication?
5. How do status transitions and idempotency avoid duplicate scheduled publication?
6. Why is LLM SEO optimization off by default?
7. Why are metadata and internal-link lengths bounded?
8. Why is a focused coverage threshold safer than 80% across legacy code?
9. Why do CI jobs use mock modes and a real PostgreSQL service?
10. What differs between GitHub service containers and GitLab CI services?
