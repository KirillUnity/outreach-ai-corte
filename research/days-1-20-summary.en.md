# Outreach AI Cortex — Days 1–20 recap

Historical study slice (EN). Current canonical recap: [Days 1–27](days-1-27-summary.en.md).
Russian historical slice: [days-1-20-summary.ru.md](days-1-20-summary.ru.md).

Slices: [1–5](days-1-5-summary.en.md) · [1–8](days-1-8-summary.en.md) · [1–12](days-1-12-summary.en.md).  
Interview roadmap: [docs/interview/ROADMAP.md](../docs/interview/ROADMAP.md). Compressed days 18–35 prompts: [docs/day-prompts/README.md](../docs/day-prompts/README.md).

**Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, PostgreSQL 16, ChromaDB, Neo4j 5, Langfuse, Poetry, Docker Compose, React/Vite.  
**Hardware:** 8 GB RAM, Iris Xe 128 MB — **no local LLMs**, no Kubernetes.  
**API:** `http://localhost:8080/api/v1` · UI: `http://localhost:3000`

---

## 1. The project in one paragraph

B2B outreach: company + lead → site parse → RAG → email discovery (patterns / Hunter / Apollo when keyed) → LangGraph (`find_email`, guardrails, **hold**) → Neo4j warm intro → mailbox warmup emulator → CRM mock → n8n JSON. Postgres is CRUD truth; Neo4j is a path index. No live SMTP, no LinkedIn scrape. Secrets stay in `.env`.

| Day | Outcome |
|-----|---------|
| 1 | Compose, FastAPI, health, Settings |
| 2 | Models, async Alembic, company CRUD |
| 3 | Person, EmailDraft, DomainHealth |
| 4 | SiteParser + research |
| 5 | LinkedIn mock/real (Phantombuster) |
| 6 | RAG / Chroma |
| 7 | LLMClient, generate-email |
| 8 | LangGraph, agent_runs |
| 9 | Langfuse, scores, alerts |
| 10 | Guardrails, RetryPolicy, analytics, PROMPTS |
| 11 | Neo4j schema and sync |
| 12 | Cypher, influence, recommendations, enrich_with_graph |
| 13 | React UI: dashboard, companies, persons, graph |
| 14 | Warm intro UI, influence, recommended targets |
| 15 | Live DNS SPF/DKIM/DMARC/MX + CLI |
| 16 | Warmup emulator, Mailbox, tick, UI |
| 17 | Email Finder, find_email node, PersonDetail |
| 18 | People-search, Apollo, Instantly-shaped sequences (no send) |
| 19 | CRM mock/Bitrix/retailCRM, n8n outreach + article stub |
| 20 | Research notes: B2B deliverability + outreach agents |

Days **21–35** exist as prompts under `docs/day-prompts/` until implemented.

---

## 2. Diagrams

### 2.1. Layers

```text
Browser :3000  →  nginx /api  →  FastAPI :8080
  routers/   HTTP, Depends
  services/  domain logic
  models/    SQLAlchemy 2
  PostgreSQL source of truth
  Chroma     RAG
  Neo4j      paths
  n8n JSON   outside Compose (RAM)
```

### 2.2. Agent (day 17+)

```text
load → research? → RAG → enrich_with_graph → find_email → generate
  → validate → deliverability snapshot → decide → save | stub send
```

`find_email` does not abort generate. Default **hold**. See [docs/agent_graph.mmd](../docs/agent_graph.mmd).

### 2.3. Mail and warmup

Finder order: LinkedIn 0.9 → Hunter ≤0.9 → Apollo ≤0.85 → patterns. Unique `(person_id, email)`. **No** live RCPT TO. Warmup is a peer simulation. Sequences tick steps only (`emails_sent=0`).

### 2.4. CRM

`CRM_PROVIDER=mock`. A Bitrix inbound webhook URL **is a secret**. Timeouts become `crm_sync_events` + HTTP 502. Do not loop CRM → agent → CRM.

---

## 3. Days 13–20

**13–14** React + warm intro. **15** Live DNS vs agent snapshot (two checker classes). **16** Warmup emulator, scheduler off by default. **17** `POST /email/find`. **18** People-search, Apollo, `/sequences`. **19** `POST /crm/sync/{person_id}`. **20** Research markdown only.

Self-check: why people-search never hits linkedin.com; why sequences are not Instantly HTTP; CRM vs Neo4j sync; why open rate is a weak KPI; why hold in dev.

---

## 4. API additions (on top of days 1–12)

| Method | Path | Role |
|--------|------|------|
| GET | `/deliverability/check/{domain}` | live DNS |
| * | `/warmup/` | emulator |
| POST/GET | `/email/find`, `/email/candidates/...` | finder |
| POST | `/enrichment/people-search` | mock people search |
| * | `/sequences/` | campaign shape, no SMTP |
| POST/GET | `/crm/sync/{id}`, `/crm/events` | CRM mock |
| UI | `/persons/:id`, `/warmup`, `/warm-intro` | React |

Days 1–12 routes: [days-1-12-summary.en.md](days-1-12-summary.en.md) §9.

---

## 5. Honest interview stack

| Yes | No |
|-----|-----|
| FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, pytest, Compose | Kubernetes, Kafka, production Redis |
| LangGraph, cloud RAG, Langfuse no-op without keys | “four years of Python microservices” |
| Mocks for Hunter/Apollo/Phantombuster/CRM/SMTP | “Instantly sends mail from this repo” |
| Git + image builds | “I shipped GitLab CI here” until prompt C8 exists |

Flashcards: [docs/interview/ROADMAP.md](../docs/interview/ROADMAP.md).

---

## 6. Commands

Same bootstrap as days 1–12, plus:

```bash
docker compose exec api poetry run alembic upgrade head
curl -s -X POST http://localhost:8080/api/v1/email/find \
  -H "Content-Type: application/json" \
  -d '{"person_id":"{id}","use_hunter":true,"use_apollo":true,"use_smtp":false}'
curl -s -X POST http://localhost:8080/api/v1/crm/sync/{id}
```

Import `n8n/workflows/*.json` in n8n UI; never commit n8n credentials.

---

## 7. Interview bank (13–20)

Deliverability: snapshot vs live; DMARC quarantine vs reject; catch-all.  
Finder: multiple candidates; no RCPT.  
Agent: find_email non-blocking; overwrite reducers.  
CRM: lead idempotency; webhook is a secret.  
Warmup: emulator vs real inbox.  
UI: PersonDetail is a route, not a modal.

---

## 8. Materials

| Topic | File |
|-------|------|
| B2B deliverability | [b2b-email-deliverability.md](b2b-email-deliverability.md) |
| Outreach agents | [ai-agents-in-b2b-outreach.md](ai-agents-in-b2b-outreach.md) |
| Email finding | [email-finding-strategies.md](email-finding-strategies.md) |
| Warmup | [warmup-mechanics.md](warmup-mechanics.md) |
| Architecture | [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) |
| Day prompts 18+ | [docs/day-prompts/README.md](../docs/day-prompts/README.md) |

---

## 9. Commits (orientation)

| Days | Prefix |
|------|--------|
| 1–12 | see 1–12 summary |
| 13 | `[FRONTEND]` |
| 14 | `[GRAPH+UI]` |
| 15 | `[DELIVERABILITY]` |
| 16 | `[WARMUP]` |
| 17 | `[EMAIL-FINDER]` |
| 18 | `[ENRICHMENT]` |
| 19 | CRM + n8n |
| 20 | `[RESEARCH]` deliverability + agents notes |
