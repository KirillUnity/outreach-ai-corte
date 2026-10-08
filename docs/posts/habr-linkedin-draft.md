# Social drafts (do not auto-publish)

Human posts these. The agent does not publish to LinkedIn or Habr. GitHub: https://github.com/KirillUnity/outreach-ai-corte

Do not paste `.env` keys “for the demo.” Do not claim the world’s first agent.

## LinkedIn (~1500 characters)

I built Outreach AI Cortex: FastAPI, PostgreSQL, Chroma, and a LangGraph agent for B2B outreach. It researches a public company site, guesses email from name patterns, drafts one message, and holds until a human says send. There is no live SMTP probe.

The same company corpus can draft an SEO article. Generate always stops at draft. A human optimizes bounded meta titles and same-company links. Publish is a mock URL or a webhook you configure, not auto-spam.

I designed it for 8 GB RAM and Intel Iris Xe (128 MB VRAM): cloud LLMs only, no Ollama, Docker Compose on one VPS, not Kubernetes. Hunter, Apollo, CRM, and CMS publish stay mock unless keys exist. n8n is JSON you import, not another container. Locust, when used, hits GET /health and GET /metrics with one user. Warmup is an emulator (no SMTP). Sequences are Instantly-shaped steps; emails_sent stays 0.

If you interview on routers vs services, unpublished Postgres, or why p95 of /health is not an agent SLO, start with DEMO.md and PROJECT_METRICS.md in the repo.

https://github.com/KirillUnity/outreach-ai-corte

<!-- Target about 1500 characters for the LinkedIn body above this comment. -->

## Habr outline (English)

Title idea: *A B2B outreach agent on an 8 GB laptop — Compose, not Kubernetes*

1. **Outreach problem.** Generic first emails, guessed addresses, no domain auth check, and the temptation to probe MX with `RCPT TO`. Why that probe is a bad idea (blocklists, catch-all). Cortex: pattern candidates, optional Hunter/Apollo clients that no-op without keys, SMTP verification off.

2. **Architecture.** FastAPI routers stay thin. Services own parser, RAG, finder, CRM, articles. Postgres is CRUD truth; Chroma is company chunks; Neo4j is an optional path index. Cloud LLM only. RAM table from DEPLOY.md. n8n workflows as files.

3. **Agent.** Eleven LangGraph nodes: load → research → RAG → graph enrich → find_email → generate → validate → deliverability → decide → save_draft or save_and_send. Default human approval = hold. Guardrails after generation. Langfuse optional.

4. **Deliverability.** Live DNS check vs `domain_health` snapshot. Warmup emulator is not Lemwarm. Sequences look Instantly-shaped but `emails_sent` is always 0.

5. **What not to do.** No live SMTP `RCPT TO`. No LinkedIn scrape. No Locust swarm on `POST /agent/outreach`. No keys in git or on a demo recording. No “we auto-publish SEO at scale.”

Closing: link GitHub, DEMO.md, honesty about 14 compressed prompts covering days 18–35 with days 25 and 30 restored later.

## How to measure the post (not vanity)

Useful: recruiter replies, screening invites, GitHub traffic from the post, questions about architecture. Weak: likes, impression charts, “first agent” framing.
