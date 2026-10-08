# How Kirill records the 5-minute demo

Day 32 already has the [screenshot checklist](SCREENSHOTS.md) and the [voiceover script](VIDEO_SCRIPT.md). This file is the human-capture half. Do not commit `.mp4` / `.mov` (gitignored). Do not commit a 50 MB binary “for the portfolio.”

## Before you press record

1. `cp .env.example .env` if needed. **Close the editor.** No `.env`, API keys, webhook URLs, or Neo4j password on screen.
2. Start the stack you actually have. Full UI: `docker compose up -d` then `alembic upgrade head`. If Docker is heavy, API-only is enough for Swagger fallback (see below).
3. Leave mocks on: `LLM_MODE=mock`, `RAG_MODE=mock`, `LINKEDIN_MODE=mock`, Hunter/Apollo off. You will say **“mock”** out loud whenever a vendor is not called.
4. Display **1920×1080**. Hide the bookmark bar if it shows mail or extra accounts. Browser zoom 100%.
5. Open tabs you will need: UI `http://localhost:3000`, Swagger `http://localhost:8080/docs`. Optional: Langfuse `:3001`, Neo4j Browser `:7474` — skip if those containers are off.
6. Print or split-screen [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md). Target ~130 words per minute. Five minutes, not fifteen.

## Record the video

Use Windows Game Bar (Win+G), OBS, or ShareX. Save locally as `outreach-ai-cortex-demo.mp4` (or `.mov`). Follow the script timestamps:

| Clock | On screen |
|-------|-----------|
| 0:00 | Dashboard or a blank slide with the problem line |
| 0:30 | Architecture or GitHub URL visible: https://github.com/KirillUnity/outreach-ai-corte |
| 1:00 | `/companies/...` research (stripe.com). Say mock if embeddings are hash vectors |
| 1:40 | `/persons/:id` email candidates. Say you are **not** calling Hunter/Apollo |
| 2:10 | Agent hold + one sentence on prompt tone (Chatix beat) |
| 2:40 | `/warmup` emulator. Say **no SMTP** |
| 3:10 | `/articles` draft. Generate stays draft; optimize; mock publish |
| 3:40 | n8n JSON in the repo (not a container). CRM mock |
| 4:10 | Limits: 8 GB, cloud LLM only, Compose not Kubernetes |
| 4:40 | CTA: questions on routers vs services, unpublished Postgres, hold |

If you stumble, keep rolling; cut later. Do not re-record because a mock name looks fake — that honesty is the point.

## Stills (filenames must match SCREENSHOTS.md)

Capture PNG at 1920×1080 into `docs/demo/` with these names (local; large binaries need not be committed):

- `01-dashboard.png`
- `02-company-research.png`
- `03-person-email-primary.png`
- `04-graph.png`
- `05-warmup.png`
- `06-articles.png`
- `07-swagger.png`
- `08-langfuse-optional.png` (only if keys exist)
- `09-neo4j-optional.png` (only if Neo4j is up)

GIF: `email-find.gif`, or the three `email-find-0N-*.png` stills. Check boxes in SCREENSHOTS.md only when the file exists.

## Where the video lives

| Place | What |
|-------|------|
| Git | Checklists and this note. Not the video. |
| Unlisted YouTube | Host the 5-minute file. Link it from DEMO.md or a PR description when you are ready. Unlisted is enough for recruiters. |
| Disk | Keep the master `.mp4` next to other portfolio assets. |

Why not git? History clones every binary forever; 50 MB videos blow GitHub warnings and slow `git clone` on a 1 GB VPS.

## Fallback if the interviewer has no Docker

Do not freeze. Walk [docs/DEMO.md](../DEMO.md) with curl snippets, open the public GitHub tree, show Swagger screenshots if you captured `07-swagger.png`, and paste `poetry run pytest -q` output from CI. Architecture mermaid in [ARCHITECTURE.md](../ARCHITECTURE.md) plus the agent node list is a better interview than a failed `compose up`. Say mock. Offer to screen-share your already-running laptop.

## Video description (paste under YouTube)

**English**

Outreach AI Cortex is a FastAPI + PostgreSQL + Chroma B2B outreach demo: company research, pattern email find (no live SMTP), a LangGraph agent that holds for a human, a warmup emulator, and draft-only SEO articles. Models are cloud APIs; the 8 GB host does not run local LLMs; production is Docker Compose, not Kubernetes. Hunter, Apollo, CRM, and publish stay mock unless keys exist. Code: https://github.com/KirillUnity/outreach-ai-corte

**Russian**

Outreach AI Cortex — демо B2B-outreach на FastAPI, PostgreSQL и Chroma: исследование сайта, поиск email по паттернам (без живого SMTP), LangGraph-агент с hold до человека, эмулятор прогрева и SEO-статьи только в draft. LLM только облачные; хост 8 ГБ без локальных моделей; прод — Docker Compose, не Kubernetes. Hunter, Apollo, CRM и публикация — мок без ключей. Код: https://github.com/KirillUnity/outreach-ai-corte
