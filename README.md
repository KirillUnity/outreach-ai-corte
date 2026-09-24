# Outreach AI Cortex

B2B outreach platform with AI agents. FastAPI + PostgreSQL + ChromaDB, all in Docker Compose.

## Stack

- Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic
- PostgreSQL 16, ChromaDB
- Docker Compose (no Kubernetes)

## Quick start

```bash
cp .env.example .env
docker compose build
docker compose up -d
docker compose exec api poetry run alembic upgrade head
curl http://localhost:8080/api/v1/health
```

## API endpoints

Base URL: `http://localhost:8080/api/v1`

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | PostgreSQL + ChromaDB + LLM config (no token spend) |

### Companies

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/companies/` | 201, 409 | Create company (domain unique) |
| GET | `/companies/` | 200 | Paginated list (`limit`, `offset`) |
| GET | `/companies/{domain}` | 200, 404 | Get by domain |
| PATCH | `/companies/{domain}` | 200, 404, 409 | Partial update |
| DELETE | `/companies/{domain}` | 204, 404 | Delete company |
| POST | `/companies/{domain}/research` | 200, 404, 502 | Parse site, save `raw_site_text`, index RAG chunks |
| GET | `/companies/{domain}/context` | 200, 404, 502 | Semantic search (`q`, `top_k`) over indexed chunks |

Example:

```bash
curl -s -X POST http://localhost:8080/api/v1/companies/ \
  -H "Content-Type: application/json" \
  -d '{"domain":"https://www.acme.com/about","name":"Acme","industry":"SaaS","size":"small"}'

curl -s http://localhost:8080/api/v1/companies/acme.com
curl -s "http://localhost:8080/api/v1/companies/?limit=20&offset=0"
curl -s -X PATCH http://localhost:8080/api/v1/companies/acme.com \
  -H "Content-Type: application/json" \
  -d '{"industry":"Fintech"}'
curl -s -o /dev/null -w "%{http_code}\n" -X DELETE http://localhost:8080/api/v1/companies/acme.com
```

`domain` is normalized: scheme, `www.`, path and port are stripped; stored as `acme.com`.

### Persons

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/persons/` | 201, 404, 409 | Create person (unique `linkedin_url` / `email`) |
| GET | `/persons/` | 200 | Paginated list (`limit`, `offset`, optional `company_id`) |
| GET | `/persons/{person_id}` | 200, 404 | Get with nested `company` |
| PATCH | `/persons/{person_id}` | 200, 404, 409 | Partial update |
| DELETE | `/persons/{person_id}` | 204, 404 | Delete person (drafts CASCADE) |
| POST | `/persons/{person_id}/company` | 200, 404 | Bind to an existing company |
| POST | `/persons/research` | 200, 400, 404, 422, 502 | Enrich from LinkedIn URL (mock or Phantombuster) |
| POST | `/persons/{person_id}/generate-email` | 200, 400, 404, 502 | RAG + LLM draft, save EmailDraft |

### Email drafts

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/email-drafts/` | 201, 404 | Create draft (`person_id` must exist) |
| GET | `/email-drafts/` | 200 | Paginated list (optional `person_id`) |
| GET | `/email-drafts/{draft_id}` | 200, 404 | Get with nested `person` |
| PATCH | `/email-drafts/{draft_id}` | 200, 404 | Partial update |
| DELETE | `/email-drafts/{draft_id}` | 204, 404 | Delete draft |
| POST | `/email-drafts/{draft_id}/mark-sent` | 200, 404 | Set `is_sent=true`, `sent_at=now(UTC)` |

### Deliverability (domain health)

Resource is named by capability, not table name: `/deliverability`.

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/deliverability/` | 201 or 200 | Upsert by domain (create / replace) |
| GET | `/deliverability/` | 200 | Paginated list |
| GET | `/deliverability/{domain}` | 200, 404 | Get by domain |
| PATCH | `/deliverability/{domain}` | 200, 404, 409 | Partial update |
| DELETE | `/deliverability/{domain}` | 204, 404 | Delete snapshot |

## Migrations

```bash
docker compose exec api poetry run alembic revision --autogenerate -m "describe change"
docker compose exec api poetry run alembic upgrade head
docker compose exec api poetry run alembic current
```

Always review the generated file under `backend/alembic/versions/` before applying.

## Site parser

`POST /api/v1/companies/{domain}/research` fetches `https://{domain}` plus a few product/about paths.

- **httpx** — async HTTP (same event loop as FastAPI)
- **trafilatura** — main-content extraction (drops nav/footer chrome)
- **BeautifulSoup + lxml** — title/meta and fallback if trafilatura returns nothing

Text is capped at `PARSER_MAX_TEXT_LENGTH` (default 50_000). Fetch failures are returned in `errors` (HTTP 200); unknown company is 404; unexpected crashes are 502.

```bash
curl -s -X POST http://localhost:8080/api/v1/companies/ \
  -H "Content-Type: application/json" \
  -d '{"domain":"stripe.com","name":"Stripe"}'

curl -s -X POST http://localhost:8080/api/v1/companies/stripe.com/research
```

The research response includes `chunks_indexed` after the site text is split and stored in Chroma.

## RAG (Chroma + cloud embeddings)

No local models. Default `RAG_MODE=mock` hashes chunks into unit vectors so CI works without an API key. `RAG_MODE=real` calls OpenAI `text-embedding-3-small` (or OpenRouter if `RAG_OPENAI_BASE_URL` is set).

- **CompanyTextSplitter** — `RecursiveCharacterTextSplitter` (1000 / 200 overlap), drop chunks shorter than 50 chars, cap source at 1M chars
- **RAGService** — delete + recreate `company_{domain}`, cosine HNSW, `tiktoken` token estimate
- **GET** `/api/v1/companies/{domain}/context?q=pricing` — top-k semantic search

```bash
curl -s "http://localhost:8080/api/v1/companies/stripe.com/context?q=pricing&top_k=3"
```

Health (`GET /api/v1/health`) pings Chroma through the shared `HttpClient` singleton.

## LinkedIn Integration

The project supports two modes. Default is **mock** so local work needs no third-party keys.

### Mock mode (default)

Deterministic fake profiles from `sha256(username)`. Same URL always yields the same name/title/company. Fine for local dev and pytest.

```
LINKEDIN_MODE=mock
```

```bash
curl -s -X POST http://localhost:8080/api/v1/persons/research \
  -H "Content-Type: application/json" \
  -d '{"linkedin_url":"https://linkedin.com/in/johndoe"}'
```

A second POST with the same URL returns `source=cache` and the same `person.id`.

### Real mode (Phantombuster)

Launches a LinkedIn Profile Scraper phantom and polls `fetch-output`. On HTTP/timeout/empty output the service **falls back to mock** and logs a warning.

```
LINKEDIN_MODE=real
PHANTOMBUSTER_API_KEY=your_key_here
LINKEDIN_PHANTOMBUSTER_PHANTOM_ID=your_agent_id
```

We never scrape LinkedIn from this repo (ToS / legal). Design notes: [research/linkedin-mock-vs-real.md](research/linkedin-mock-vs-real.md).

## Email generation

`POST /api/v1/persons/{person_id}/generate-email` runs: **RAG retrieve → prompt → cloud LLM → validate → save EmailDraft**.

Default `LLM_MODE=mock` returns a deterministic JSON draft so CI spends no tokens. `LLM_MODE=real` calls OpenAI or OpenRouter (`gpt-4o-mini` in dev, `gpt-4o` as `PREMIUM_MODEL`). Sender identity is passed per request, not stored as a user table.

```bash
curl -s -X POST http://localhost:8080/api/v1/persons/{person_id}/generate-email \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "{person_id}",
    "goal": "meeting",
    "tone": "professional",
    "max_words": 120,
    "language": "en",
    "sender_name": "Kirill",
    "sender_title": "Founder",
    "sender_company": "AI Cortex"
  }'
```

Prompt notes: [research/llm-prompt-engineering-for-outreach.md](research/llm-prompt-engineering-for-outreach.md) · all templates: [PROMPTS.md](PROMPTS.md)

## Docs

- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc
