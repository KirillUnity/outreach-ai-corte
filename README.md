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
| GET | `/health` | PostgreSQL + ChromaDB status |

### Companies

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/companies/` | 201, 409 | Create company (domain unique) |
| GET | `/companies/` | 200 | Paginated list (`limit`, `offset`) |
| GET | `/companies/{domain}` | 200, 404 | Get by domain |
| PATCH | `/companies/{domain}` | 200, 404, 409 | Partial update |
| DELETE | `/companies/{domain}` | 204, 404 | Delete company |

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

## Migrations

```bash
docker compose exec api poetry run alembic revision --autogenerate -m "describe change"
docker compose exec api poetry run alembic upgrade head
docker compose exec api poetry run alembic current
```

Always review the generated file under `backend/alembic/versions/` before applying.

## Docs

- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc
