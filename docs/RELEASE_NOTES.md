# Release notes — days 1–35 (compressed)

Honest timeline. Days **1–17** were built as a daily track on FastAPI, Postgres, RAG, LangGraph, UI, finder, warmup, and deliverability. Days **18–35** were executed as **14 compressed prompts** (`docs/day-prompts/`). **Days 25 and 30** were skipped in that pack and **restored in this batch**. **Day 33** is capture notes (`docs/demo/CAPTURE.md`), not a recorded video file in git.

## Days 1–12 — platform

Bootstrap FastAPI + async SQLAlchemy + PostgreSQL 16, company/person/email drafts, site parser, cloud RAG (Chroma) and LLM wrappers with mock modes, LangGraph outreach agent, Langfuse tracing, guardrails, analytics, Neo4j graph index.

## Days 13–17 — UI and deliverability

React/Vite admin, warm-intro paths, live DNS deliverability, mailbox warmup emulator, pattern + Hunter email candidates. Live SMTP `RCPT TO` remains disabled.

## Days 18–20 — enrichment, CRM, research notes

Mock-first people search, Apollo adapter, Instantly-shaped sequences without send, Bitrix/retailCRM mock + n8n JSON, research notes on deliverability and agents.

## Days 21–24 — SEO factory

`SEOArticle`, RAG `ArticleGenerator`, draft-only generate, mock/webhook publisher, schedule + admin tick, UI list/preview, deterministic meta/keywords/same-company links (compressed prompt labeled day 23 covered former day 24 SEO fields).

## Day 25 — content-marketing essay (restored)

[research/content-marketing-b2b-seo.md](../research/content-marketing-b2b-seo.md): shared company corpus, editorial hold, honest limits.

## Days 26–29 — tests, CI, VPS, observability

Focused pytest/Vitest, GitHub Actions + GitLab CI (Postgres 16, mocks, no deploy), `docker-compose.prod.yml` + [DEPLOY.md](DEPLOY.md), Sentry, `GET /metrics`, Langfuse prod notes.

## Day 30 — Locust (restored)

Optional Poetry group `load`, read-only `loadtest/locustfile.py`, [LOAD_TESTING.md](LOAD_TESTING.md). Not in Compose. Not in CI. Not a swarm against the agent.

## Days 31–32 — docs and demo checklist

[ARCHITECTURE.md](ARCHITECTURE.md), [DEMO.md](DEMO.md), PROMPTS catalog, [SCREENSHOTS.md](demo/SCREENSHOTS.md), [VIDEO_SCRIPT.md](demo/VIDEO_SCRIPT.md).

## Day 33 — capture notes (not a git binary)

[CAPTURE.md](demo/CAPTURE.md): how to record 1920×1080, say “mock,” host unlisted YouTube, keep mp4 out of git.

## Day 34 — interview answers

[docs/interview/ANSWERS.md](interview/ANSWERS.md) aligned to otklik docs.

## Day 35 — ship docs (files only)

[PROJECT_METRICS.md](PROJECT_METRICS.md), [posts/habr-linkedin-draft.md](posts/habr-linkedin-draft.md), this file. No git commit/push in the restore batch; no social publish.

## Recap

Canonical 1–35: [research/days-1-35-summary.en.md](../research/days-1-35-summary.en.md) / [ru](../research/days-1-35-summary.ru.md). Older slices (1–8, 1–12, 1–20, 1–27) stay in `research/`.
