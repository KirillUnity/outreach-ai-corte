# День 28 (сжатый C9) — Деплой VPS Docker Compose (не K8s)

```
<SYSTEM>

ROLE & MISSION
Tech Lead. Целевая машина как у проекта: мало RAM. Oracle Free / Hetzner CX22. ЗАПРЕЩЕНО: kubernetes, helm, minikube, k3s в доках как «рекомендуемый прод».

PROJECT STATE
docker-compose.yml dev со стеком postgres, chroma, neo4j, langfuse, frontend, api. mem_limit уже местами есть.

TASK

БЛОК 1: // docker-compose.prod.yml
Профиль без Langfuse+Neo4j по умолчанию (profiles: extra) чтобы 1 GB VPS выжил.
api + postgres + frontend (+ chroma если RAG real).
restart unless-stopped, healthcheck, mem_limit.
Нет published 5432 на 0.0.0.0 — только internal network.

БЛОК 2: // docs/DEPLOY.md
- DNS A record
- Caddy or nginx TLS (кратко, один пример Caddyfile)
- cp .env.example .env, секреты
- alembic upgrade head
- RAM table: api 512m, postgres 512m, frontend 64m, chroma 256m
- Что выключить: NEO4J, LANGFUSE на 1 GB
- Backup: pg_dump cron
Не Ansible на 15 ролей.

БЛОК 3: // docker-compose.prod.yml env_file .env
FRONTEND API proxy на тот же хост.

БЛОК 4: Чеклист rollback: предыдущий image tag.

Проверочные вопросы:
1. Почему Postgres не публиковать на интернет?
2. Зачем profiles для Neo4j?
3. Compose vs K8s для соло-VPS?
4. Как не потерять volume при recreate?
5. LLM ключи только в env, не в image?

OUTPUT CONTRACT
Документ, по которому можно поднять стек за час. Реальный заказ Oracle не обязателен в этом чате.

ОБУЧЕНИЕ
Docker Compose production; Caddy automatic HTTPS; pg_dump.

ВОПРОСЫ НА СОБЕС
1. 12-factor config
2. Blue-green без k8s
3. Healthcheck vs /health
4. Log rotation
5. Что делать если 8 GB host и все профили включены
```
