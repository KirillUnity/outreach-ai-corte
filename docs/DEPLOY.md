# Deploy on one VPS (Docker Compose)

Target: a small Linux VPS, about an hour, no control plane. The dev machine budget is 8 GB RAM. A 1 GB VPS runs only the default profile below. This file does not order a server.

Cloud LLMs only. Do not add a local model server. Do not treat Kubernetes, Helm, Minikube, or k3s as the production path for this project.

## RAM

| Service | Limit | Default `up` |
|---------|------:|:------------:|
| api | 512m | yes |
| postgres | 512m | yes |
| frontend | 64m | yes |
| chroma | 256m | profile `rag` only |
| neo4j | 768m | profile `extra` — **off** |
| langfuse + its Postgres | 512m + 256m | profile `extra` — **off** |

Default limits already sum to about 1.1 GB before the operating system. On a 1 GB box, add a small swap file and do not enable `rag` or `extra`. Company research stores vectors in Chroma even when `RAG_MODE=mock`, so indexing needs `--profile rag` and a box closer to 2 GB. Turn **Neo4j** and **Langfuse** off on 1 GB (`NEO4J_ENABLED=false` in `.env`, and do not pass `--profile extra`).

## 1. DNS

Create an **A record** from the hostname you will serve (for example `app.example.com`) to the VPS IPv4 address. Wait until `dig +short app.example.com` returns that address. Caddy needs the name to match before it can fetch a certificate.

## 2. Env file

On the server, in the clone:

```bash
cp .env.example .env
chmod 600 .env
```

Secrets live only in that file (and in the host secret store you copy them from): `POSTGRES_PASSWORD`, `OPENAI_API_KEY` / `OPENROUTER_API_KEY`, `NEO4J_PASSWORD`, CRM webhook URLs, Hunter/Apollo/Phantombuster keys. They are not baked into the image. Set at least:

- `POSTGRES_PASSWORD` — replace the example value
- `DATABASE_URL` — host must stay `postgres` (the Compose service name), not `localhost`
- `NEO4J_ENABLED=false` and `LANGFUSE_ENABLED=false` on a 1 GB VPS
- `LLM_MODE=mock` until you intentionally spend tokens

## 3. Start

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec api poetry run alembic upgrade head
curl -s http://127.0.0.1:8080/metrics | head
curl -s http://127.0.0.1:8080/api/v1/health
```

Postgres has **no published port**. The API port is bound to `127.0.0.1:8080` for curl and a local metrics scrape. The browser uses `https://app.example.com` only. nginx inside the frontend container proxies `/api/` to `http://api:8080` on the Compose network, so the UI and the API share one public host.

`GET /api/v1/health` returns 503 while Chroma is absent. That is expected on the default profile. Container health uses `GET /metrics`, which does not require Chroma.

Optional later (not on 1 GB):

```bash
docker compose -f docker-compose.prod.yml --profile rag up -d
docker compose -f docker-compose.prod.yml --profile extra up -d
```

## 4. TLS (Caddy on the host)

Install Caddy on the host so ports 80 and 443 are not another container. One site:

```caddyfile
app.example.com {
	reverse_proxy 127.0.0.1:3000
}
```

Do not add a route to `/metrics` or to port 8080. Open ports 22, 80, and 443 only.

## 5. Backup

Cron on the host (daily, keep a week). This reads the internal Postgres; it does not open 5432:

```bash
0 3 * * * docker compose -f /opt/outreach/docker-compose.prod.yml exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > /var/backups/outreach-$(date +\%F).sql.gz
find /var/backups -name 'outreach-*.sql.gz' -mtime +7 -delete
```

Restore into the existing volume: `gunzip -c file.sql.gz | docker compose -f docker-compose.prod.yml exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"`.

## 6. Rollback

1. Before you build a new release, keep the current images:
   ```bash
   docker tag outreach-api:local outreach-api:previous
   docker tag outreach-frontend:local outreach-frontend:previous
   ```
2. To roll back, point Compose at that tag and do not rebuild:
   ```bash
   IMAGE_TAG=previous docker compose -f docker-compose.prod.yml up -d --no-build
   ```
3. Do not drop the database volume. `docker compose up -d` and `up -d --force-recreate` replace containers and **keep** named volumes (`outreach-prod_postgres_data`, `outreach-prod_chroma_data`). `docker compose down` also keeps volumes.
4. `docker compose down -v` and `docker volume rm` delete data. Do not use them in a rollback.
5. Do not rename the volume key `postgres_data` in this file between releases. A new key means a new empty volume.
6. After rollback, run `alembic upgrade head` only if the previous image’s migrations are still a fast-forward. If the new release already migrated, restore the SQL dump instead of guessing a downgrade.

Logs are rotated by the json-file driver (`max-size` 10m, 3 files) so a chatty API cannot fill the disk.
