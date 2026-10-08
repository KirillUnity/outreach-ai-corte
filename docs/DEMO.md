# Demo (about 10 minutes)

Mock mode spends no tokens. Say "mock" when a step is not calling a vendor. UI: http://localhost:3000. API: http://localhost:8080/api/v1. Swagger: http://localhost:8080/docs.

```bash
cp .env.example .env
docker compose up -d
docker compose exec api poetry run alembic upgrade head
```

Leave `LLM_MODE=mock`, `RAG_MODE=mock`, `LINKEDIN_MODE=mock`, `HUNTER_ENABLED=false`, `APOLLO_ENABLED=false`.

## 1. Health

```bash
curl -s http://localhost:8080/api/v1/health
```

Expect Postgres up. LLM detail says `mock mode`. Neo4j is up only if that container is running. This call does not spend tokens.

## 2. Company research (stripe.com)

```bash
curl -s -X POST http://localhost:8080/api/v1/companies/ \
  -H "Content-Type: application/json" \
  -d '{"domain":"stripe.com","name":"Stripe"}'

curl -s -X POST http://localhost:8080/api/v1/companies/stripe.com/research
curl -s "http://localhost:8080/api/v1/companies/stripe.com/context?q=payments&top_k=3"
```

Research fetches the public site and indexes chunks. Embeddings are hash vectors in mock mode, still stored in Chroma. Open `/companies/stripe.com` and show research plus recommended targets if the graph has been synced.

## 3. Person research

```bash
curl -s -X POST http://localhost:8080/api/v1/persons/research \
  -H "Content-Type: application/json" \
  -d '{"linkedin_url":"https://www.linkedin.com/in/demo-stripe","company_domain":"stripe.com"}'
```

Default source is **mock**: the same URL always yields the same name and title. Copy `person.id` from the JSON. This is not a LinkedIn scrape.

## 4. Email find

```bash
curl -s -X POST http://localhost:8080/api/v1/email/find \
  -H "Content-Type: application/json" \
  -d '{"person_id":"PERSON_ID","use_hunter":false,"use_apollo":false,"use_smtp":false}'
```

Candidates are name patterns (`first.last`, `flast`, and the rest of the list in settings). Confidence at or above 0.6 can be primary. `use_smtp` stays false: there is no live `RCPT TO`. On `/persons/:id`, point at source badges and the PRIMARY mark.

## 5. Agent outreach — hold

```bash
curl -s -X POST http://localhost:8080/api/v1/agent/outreach \
  -H "Content-Type: application/json" \
  -d '{
    "person_id":"PERSON_ID",
    "goal":"meeting",
    "sender_name":"Kirill",
    "sender_title":"Founder",
    "sender_company":"AI Cortex",
    "language":"en",
    "max_words":120
  }'
```

Expect `decision` `hold` and `decision_reason` `awaiting approval` while `AGENT_REQUIRE_HUMAN_APPROVAL=true`. The draft is saved. Nothing is sent. Guardrails cover PII, spammy content, invented facts, length, and a single CTA.

## 6. Warmup tick

```bash
curl -s -X POST http://localhost:8080/api/v1/warmup/mailboxes \
  -H "Content-Type: application/json" \
  -d '{"email":"sender@example.com","display_name":"Kirill"}'
```

Start that mailbox, then `POST /api/v1/warmup/mailboxes/{id}/tick`. Open `/warmup` and show the mailbox card and timeline. Opens and replies are simulated. No SMTP.

## 7. Article generate and optimize

```bash
curl -s -X POST http://localhost:8080/api/v1/articles/generate \
  -H "Content-Type: application/json" \
  -d '{"company_domain":"stripe.com","keyword":"payment infrastructure","language":"en","max_words":400}'
```

Then `POST /api/v1/articles/{id}/optimize`. Generate writes a draft from company context (mock LLM text when `LLM_MODE=mock`). Optimize fills meta title, description, keywords, and safe internal links without another model call. Preview on `/articles`. Publish stays on the mock channel unless `CONTENT_PUBLISH_WEBHOOK_URL` is set.

## 8. What does nothing without keys

| Integration | Without a key |
|-------------|----------------|
| Hunter | `HunterClient` returns `[]`. Patterns still run. |
| Apollo | `ApolloClient` returns `[]`. |
| Phantombuster | `LINKEDIN_MODE=real` falls back to mock if the key or phantom id is missing or the HTTP call fails. |
| OpenAI / OpenRouter | Stay on `LLM_MODE=mock` / `RAG_MODE=mock`. |
| Bitrix24 / retailCRM | `CRM_PROVIDER=mock` writes a local sync row and does not call the vendor. |
| Instantly | Not integrated. Sequences only advance `current_step` in Postgres. |
| n8n | Not in Compose. Import `n8n/workflows/*.json` yourself. |

If a key is absent, do not describe the step as a live vendor integration.
