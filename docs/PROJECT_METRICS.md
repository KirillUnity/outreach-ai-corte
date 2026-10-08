# Project metrics (counted from this tree)

Snapshot for the Day 35 portfolio pack. Numbers come from files in git, not from a marketing slide. Recount after large refactors.

Counted: Compose YAML service keys, `class …(Base)` table models, `include_router` in `backend/app/main.py`, `workflow.add_node` in `backend/app/services/agent/graph.py`, `n8n/workflows/*.json`, line count of `PROMPTS.md`, `backend/tests/test_*.py`, RAM table copied from [DEPLOY.md](DEPLOY.md).

## Compose services

| File | Service keys | Who starts |
|------|-------------:|------------|
| `docker-compose.yml` (dev) | **7** | Always: `postgres`, `chromadb`, `api`, `frontend`, `neo4j`, `langfuse-db`, `langfuse` |
| `docker-compose.prod.yml` | **7** | Default `up`: `postgres`, `api`, `frontend` (**3**). Profile `rag`: `chromadb`. Profile `extra`: `neo4j`, `langfuse-db`, `langfuse` |

n8n is **not** a Compose service. Locust is **not** a Compose service.

## SQLAlchemy models

**12** mapped tables (exclude `Base` and enum-only modules):

`Company`, `Person`, `EmailDraft`, `EmailCandidate`, `AgentRun`, `DomainHealth`, `Mailbox`, `WarmupEvent`, `OutreachSequence`, `OutreachSequenceEnrollment`, `CrmSyncEvent`, `SEOArticle`.

## HTTP routers

**14** routers mounted under `/api/v1`: `health`, `articles`, `companies`, `persons`, `email_drafts`, `email_finder`, `enrichment`, `sequences`, `crm`, `domain_health`, `agent`, `analytics`, `graph`, `warmup`.

**1** extra scrape route, not under `/api/v1`: `GET /metrics` (`metrics.router`).

## LangGraph node names

**11** nodes in `build_outreach_graph()`:

`load_person`, `research_company`, `retrieve_rag`, `enrich_with_graph`, `find_email`, `generate_email`, `validate_email`, `check_deliverability`, `decide`, `save_draft`, `save_and_send`.

## n8n workflows

**3** JSON files in `n8n/workflows/`: `warmup_tick.json`, `outreach_run.json`, `article_publish.json`. Import in your n8n UI. Credentials stay in n8n env.

## Prompt catalog size

`PROMPTS.md`: **109** lines (v1.3 catalog; implementation lives in `backend/app/services/prompts/`).

## Pytest files

**45** files matching `backend/tests/test_*.py` (plus `conftest.py`, not counted as a test module). Includes restored Locust smoke `test_locustfile.py`.

## RAM budget (production Compose)

From [DEPLOY.md](DEPLOY.md):

| Service | Limit | Default `up` |
|---------|------:|:------------:|
| api | 512m | yes |
| postgres | 512m | yes |
| frontend | 64m | yes |
| chroma | 256m | profile `rag` only |
| neo4j | 768m | profile `extra` — **off** |
| langfuse + its Postgres | 512m + 256m | profile `extra` — **off** |

Default limits already sum to about 1.1 GB before the operating system. Dev Compose caps are higher (Chroma 768m, frontend 128m, Neo4j 1024m, Langfuse 768m + 256m) and still target ≤ ~4 GB of container RAM on an 8 GB host.

## Honest mocks

| Piece | Default |
|-------|---------|
| Hunter | Client returns empty without flag + key. Patterns still run. |
| Apollo | Same. No people/match HTTP without `APOLLO_ENABLED` + key. |
| SMTP | `SMTP_VERIFICATION_ENABLED=false`. No live `RCPT TO`. `save_and_send` does not open a mail session. |
| CRM | `CRM_PROVIDER=mock`. Bitrix/retailCRM HTTP only with webhook or key (never commit the Bitrix inbound path). |
| Publish | Mock URL on `example.invalid` unless `CONTENT_PUBLISH_WEBHOOK_URL` is set. |
| LinkedIn | `LINKEDIN_MODE=mock`. This repo does not scrape. Phantombuster falls back to mock. |
| LLM / RAG | `mock` in CI and local default. Real mode is cloud APIs only. |
| Sequences | Instantly-shaped steps; `emails_sent` stays 0. |
| Warmup | Emulator. No SMTP. |

Do not quote these as live vendor integrations in a demo without keys.
