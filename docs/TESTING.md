# Testing

The suite is deliberately mock-first: CI must not spend LLM tokens, probe SMTP recipients, scrape
LinkedIn, or require Chroma/Neo4j/Langfuse.

## Pyramid

1. Service units cover orchestration, validation, fallback, idempotency, and state transitions.
2. HTTP adapter tests use `httpx.MockTransport`; third-party APIs are never called live.
3. FastAPI tests validate routing and Pydantic contracts.
4. Docker Compose integration tests use PostgreSQL and are marked `@pytest.mark.integration`.
   They should skip when `http://localhost:8080` is unavailable.
5. Vitest + React Testing Library covers thin UI states. Browser E2E is intentionally omitted to
   keep memory use low.

## Commands

```bash
poetry run pytest -q
poetry run pytest --cov=app --cov-report=term-missing --cov-fail-under=0
poetry run pytest backend/tests/test_email_finder.py backend/tests/test_apollo_client.py \
  backend/tests/test_crm.py backend/tests/test_articles.py \
  --cov=app.services.email_finder --cov=app.services.crm \
  --cov=app.services.article_generator --cov-fail-under=70

cd frontend
npm ci
npm test
npm run build
```

The project does not impose 80% on the whole legacy application. The focused 70% threshold applies
to new Days 17–23 service packages; broad coverage remains informational.
