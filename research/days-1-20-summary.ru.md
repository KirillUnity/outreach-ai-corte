# Outreach AI Cortex — итоги дней 1–20

Исторический срез (RU). Текущая каноническая шпаргалка: [дни 1–27](days-1-27-summary.ru.md).
English historical slice: [days-1-20-summary.en.md](days-1-20-summary.en.md).

Срезы: [1–5](days-1-5-summary.ru.md) · [1–8](days-1-8-summary.ru.md) · [1–12](days-1-12-summary.ru.md) (граф/агент до warm intro API).  
Собес-roadmap: [docs/interview/ROADMAP.md](../docs/interview/ROADMAP.md). Сжатый трек 18–35: [docs/day-prompts/README.md](../docs/day-prompts/README.md).

**Стек:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, PostgreSQL 16, ChromaDB, Neo4j 5, Langfuse, Poetry, Docker Compose, React/Vite.  
**Железо:** 8 GB RAM, Iris Xe 128 MB — **нет локальных LLM**, нет Kubernetes.  
**API:** `http://localhost:8080/api/v1` · UI: `http://localhost:3000`  
**Ветка:** часто `cursor/day1-bootstrap-fastapi-stack`.

---

## 1. Проект в одном абзаце

B2B-outreach: компания + лид → парсинг сайта → RAG → поиск email (паттерны / Hunter / Apollo-мок) → LangGraph (find_email, guardrails, **hold**) → граф знакомств Neo4j → эмулятор прогрева ящика → CRM-мок (Bitrix/retailCRM) → n8n JSON. Postgres — CRUD; Neo4j — пути. Секреты только в `.env`. Живого SMTP и скрейпа LinkedIn нет.

| День | Суть |
|------|------|
| 1 | Compose, FastAPI, health, Settings |
| 2 | Модели, Alembic async, CRUD companies |
| 3 | Person, EmailDraft, DomainHealth |
| 4 | SiteParser + research сайта |
| 5 | LinkedIn mock/real (Phantombuster) |
| 6 | RAG Chroma |
| 7 | LLMClient, generate-email |
| 8 | LangGraph, agent_runs |
| 9 | Langfuse, scores, alerts |
| 10 | Guardrails, RetryPolicy, analytics, PROMPTS |
| 11 | Neo4j схема и sync |
| 12 | Cypher, influence, recommendations, enrich_with_graph |
| 13 | React UI: dashboard, companies, persons, graph |
| 14 | Warm intro UI, influence badge, recommended targets |
| 15 | Live DNS SPF/DKIM/DMARC/MX + CLI |
| 16 | Warmup emulator, Mailbox, tick, UI |
| 17 | Email Finder: patterns, Hunter, SMTP-мок, нода find_email, PersonDetail |
| 18 | People-search, Apollo, Instantly-shaped Sequence (без send) |
| 19 | CRM mock/Bitrix/retailCRM, n8n outreach + article stub |
| 20 | Research: deliverability B2B + AI-агенты (этот день — markdown) |

Дни **21–35** сжатого трека — промпты в `docs/day-prompts/` (статьи, CI, VPS); в коде ещё нет, пока не реализованы отдельными чатами.

---

## 2. Схемы

### 2.1. Слои

```text
Browser :3000  →  nginx /api  →  FastAPI :8080
  routers/   HTTP, Depends
  services/  бизнес-логика
  models/    SQLAlchemy 2
  PostgreSQL source of truth
  Chroma     RAG
  Neo4j      paths
  n8n JSON   снаружи Compose (RAM)
```

### 2.2. Агент (день 17+)

```text
load → research? → RAG → enrich_with_graph → find_email → generate
  → validate → deliverability snapshot → decide → save | stub send
```

`find_email` не стопает generate. `human_approval` → hold. Диаграмма: [docs/agent_graph.mmd](../docs/agent_graph.mmd).

### 2.3. Почта и прогрев

Finder: LinkedIn email 0.9 → Hunter ≤0.9 → Apollo ≤0.85 → паттерны. Unique `(person_id, email)`. SMTP RCPT **запрещён**.  
Warmup: симуляция peer, `POST /warmup/tick-all` + n8n.  
Sequence: tick шагов, `emails_sent=0`.

### 2.4. CRM

`CRM_PROVIDER=mock`. Bitrix webhook URL — **секрет**. 401/timeout → `crm_sync_events.status=error` + HTTP 502. Не зацикливать CRM → agent → CRM.

---

## 3. Дни 13–20 (подробно)

**13–14 UI/граф:** Vite+Tailwind, `/graph`, `/warm-intro`, influence.  
**15 Deliverability:** live DNS vs snapshot для агента — два класса, не путать.  
**16 Warmup:** MailboxStatus, reputation, scheduler выключен по умолчанию.  
**17 Finder:** `POST /email/find`, UI `/persons/:id`.  
**18 Enrichment:** `POST /enrichment/people-search`, Apollo client, `/sequences`.  
**19 CRM:** `POST /crm/sync/{person_id}`.  
**20 Notes:** [b2b-email-deliverability.md](b2b-email-deliverability.md), [ai-agents-in-b2b-outreach.md](ai-agents-in-b2b-outreach.md).

Самопроверка 13–20: зачем people-search не ходит на linkedin.com? почему sequence не Instantly API? чем CRM sync отличается от Neo4j sync? почему open rate плохая KPI? зачем hold в dev?

---

## 4. Карта API (добавки к 1–12)

| Метод | Путь | Смысл |
|--------|------|--------|
| GET/POST | `/deliverability/check/{domain}` | live DNS |
| * | `/warmup/` | emulator |
| POST/GET | `/email/find`, `/email/candidates/...` | finder |
| POST | `/enrichment/people-search` | мок SN-like |
| * | `/sequences/` | кампания без SMTP |
| POST/GET | `/crm/sync/{id}`, `/crm/events` | CRM-мок |
| UI | `/persons/:id`, `/warmup`, `/warm-intro` | React |

Полный список 1–12: [days-1-12-summary.ru.md](days-1-12-summary.ru.md) §9.

---

## 5. Честный стек на собесе

| Говорить да | Говорить нет |
|-------------|--------------|
| FastAPI, Pydantic v2, SQLAlchemy 2 async, Alembic, pytest, Compose | Kubernetes, Kafka, Redis прод |
| LangGraph, RAG cloud, Langfuse no-op без ключей | 4 года Python-микросервисов |
| Моки Hunter/Apollo/Phantombuster/CRM/SMTP | «интеграция Instantly шлёт письма» |
| Git + Docker images | «я настроил GitLab CI в этом репо» — пока нет YAML (промпт C8) |

Карточки: [docs/interview/ROADMAP.md](../docs/interview/ROADMAP.md).

---

## 6. Команды

Как в [days-1-12](days-1-12-summary.ru.md) §10, плюс:

```bash
docker compose exec api poetry run alembic upgrade head
curl -s -X POST http://localhost:8080/api/v1/email/find \
  -H "Content-Type: application/json" \
  -d '{"person_id":"{id}","use_hunter":true,"use_apollo":true,"use_smtp":false}'
curl -s -X POST http://localhost:8080/api/v1/crm/sync/{id}
```

n8n: Import from File `n8n/workflows/*.json` — не класть credentials в git.

---

## 7. Банк вопросов (добавка 13–20)

Deliverability: snapshot vs live; DMARC quarantine vs reject; catch-all.  
Finder: несколько candidates; почему не RCPT.  
Агент: find_email не блокирует; overwrite reducers.  
CRM: идемпотентность лида; webhook = секрет.  
Warmup: emulator vs реальный inbox.  
UI: PersonDetail не модалка — shareable URL.

---

## 8. Материалы

| Тема | Файл |
|------|------|
| Deliverability B2B | [b2b-email-deliverability.md](b2b-email-deliverability.md) |
| Агенты B2B | [ai-agents-in-b2b-outreach.md](ai-agents-in-b2b-outreach.md) |
| Finder | [email-finding-strategies.md](email-finding-strategies.md) |
| Warmup | [warmup-mechanics.md](warmup-mechanics.md) |
| Архитектура | [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) |
| Промпты дней 18+ | [docs/day-prompts/README.md](../docs/day-prompts/README.md) |

---

## 9. Коммиты (ориентир)

| Дни | Префикс |
|-----|---------|
| 1–12 | см. 1–12 summary |
| 13 | `[FRONTEND]` |
| 14 | `[GRAPH+UI]` |
| 15 | `[DELIVERABILITY]` |
| 16 | `[WARMUP]` |
| 17 | `[EMAIL-FINDER]` |
| 18 | `[ENRICHMENT]` |
| 19 | CRM + n8n (если закоммичено) |
| 20 | `[RESEARCH]` deliverability + agents notes |
