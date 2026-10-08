# Outreach AI Cortex — канонические итоги дней 1–35

English: [days-1-35-summary.en.md](days-1-35-summary.en.md). Исторические срезы остаются в репо:
[1–27](days-1-27-summary.ru.md), [1–20](days-1-20-summary.ru.md), [1–12](days-1-12-summary.ru.md) и
[1–8](days-1-8-summary.ru.md). Старые файлы не удалять.

Честный темп: дни 1–17 — ежедневная сборка. Дни 18–35 — **14 сжатых промптов**
(`docs/day-prompts/`). **Дни 25 и 30** в том пакете были пропущены и восстановлены здесь.
**День 33** — инструкция по записи, а не mp4 в git.

## Архитектура

Python 3.12, FastAPI, async SQLAlchemy 2.0, PostgreSQL 16, ChromaDB, Neo4j,
React/Vite, Poetry и Docker Compose. Продовые LLM/embedding-вызовы идут только в облачные API;
mock-режимы делают локальную разработку и CI детерминированными. Postgres — источник CRUD-данных,
Chroma — RAG-чанки компаний, Neo4j — индекс связей и путей. Прод на VPS — всё ещё Compose
([docs/DEPLOY.md](../docs/DEPLOY.md)): по умолчанию api + postgres + frontend; Chroma — профиль
`rag`; Neo4j и Langfuse — профиль `extra`. Kubernetes не является прод-путём. Locust — опциональная
группа Poetry, не контейнер.

Счётчики: [docs/PROJECT_METRICS.md](../docs/PROJECT_METRICS.md). Демо:
[docs/DEMO.md](../docs/DEMO.md). Changelog: [docs/RELEASE_NOTES.md](../docs/RELEASE_NOTES.md).

## Хронология

- Дни 1–12: bootstrap, модели company/person/email, исследование сайтов, cloud RAG/LLM,
  LangGraph-агент, наблюдаемость, guardrails, аналитика и граф.
- Дни 13–17: React-админка, warm intro, DNS-deliverability, эмулятор прогрева и кандидаты email.
  Живой SMTP RCPT остаётся выключенным.
- Дни 18–20: mock-first people search, Apollo, sequence state machine, CRM-адаптеры, n8n и
  исследовательские заметки.
- День 21: `SEOArticle`, версионированные промпты, RAG `ArticleGenerator`, CRUD/generate API,
  токены/стоимость и генерация только в draft.
- День 22: идемпотентный mock/webhook publisher, очередь по расписанию, защищённый admin tick,
  hourly n8n и лёгкий UI списка/генерации/preview.
- День 23: детерминированные meta-поля, ограниченные keywords, безопасные ссылки внутри компании,
  опциональный единичный LLM-вызов и кнопка Optimize (поля SEO в исходном календаре были днём 24).
- День 25 (восстановлен): эссе
  [research/content-marketing-b2b-seo.md](content-marketing-b2b-seo.md).
- День 26: сфокусированные backend-тесты, SMTP-disabled/duplicate/empty-result ветки, Vitest UI и
  [инструкция по тестам](../docs/TESTING.md).
- День 27: GitHub Actions и GitLab CI с PostgreSQL 16, mock-режимами, backend/frontend
  тестами и build без deploy.
- День 28: `docker-compose.prod.yml`, таблица RAM, Caddy на хосте, бэкапы, откат.
- День 29: Sentry, Prometheus `GET /metrics`, заметки Langfuse в проде
  ([docs/OBSERVABILITY.md](../docs/OBSERVABILITY.md)).
- День 30 (восстановлен): Locust только на health и metrics
  ([docs/LOAD_TESTING.md](../docs/LOAD_TESTING.md)).
- День 31: ARCHITECTURE, DEMO, каталог PROMPTS.
- День 32: чеклист скринов и сценарий 5-минутного видео
  ([SCREENSHOTS.md](../docs/demo/SCREENSHOTS.md),
  [VIDEO_SCRIPT.md](../docs/demo/VIDEO_SCRIPT.md)).
- День 33: как записать и где хостить видео
  ([CAPTURE.md](../docs/demo/CAPTURE.md)); бинарники не в git.
- День 34: ответы к собесу ([docs/interview/ANSWERS.md](../docs/interview/ANSWERS.md)).
- День 35: метрики, черновики постов, release notes. В restore-батче только файлы (без commit/push
  и без публикации в соцсети).

## Жизненный цикл статьи

`Company.raw_site_text → Chroma retrieval → версионированный JSON prompt →
SEOArticle(draft) → review/optimize → scheduled → admin tick → mock или webhook publish`.

Generate никогда не публикует автоматически. Mock URL использует `example.invalid`; ошибка
webhook переводит статью в failed. Internal links ограничены доменом компании и путями сохранённых
статей. Повторный publish — no-op.

Outreach и SEO делят один корпус. Editorial hold — аналог `AGENT_REQUIRE_HUMAN_APPROVAL`.

## Проверка

```bash
poetry run pytest -q
poetry run pytest --cov=app --cov-report=term-missing --cov-fail-under=0
cd frontend && npm ci && npm test && npm run build
docker compose exec api poetry run alembic upgrade head
poetry install --with load
poetry run locust -f loadtest/locustfile.py --host http://127.0.0.1:8080 --users 1 --spawn-rate 1 --headless -t 30s
```

CI использует Python 3.12, Node 20 и PostgreSQL 16. Chroma, Neo4j, Langfuse, Locust и весь Compose
там не стартуют. Секреты внешних сервисов не требуются. Не нагружать `POST /agent/outreach`.

Портфолио: [DEMO.md](../docs/DEMO.md). Запись: [CAPTURE.md](../docs/demo/CAPTURE.md).
VPS: [DEPLOY.md](../docs/DEPLOY.md).

## Самопроверка / собеседование

1. Почему статья относится к Company, а не Person?
2. Почему JSON от LLM безопаснее сырого markdown?
3. Как RAG и editorial disclaimer уменьшают риск галлюцинаций?
4. Почему generate заканчивается статусом draft и кто утверждает публикацию?
5. Как status transition и идемпотентность защищают от дублей?
6. Почему LLM-SEO выключен по умолчанию?
7. Зачем ограничивать длину meta и число внутренних ссылок? Почему только same-company?
8. Почему 70% для новых пакетов лучше, чем 80% для всего legacy?
9. Зачем CI mock-режимы и настоящий PostgreSQL service?
10. Чем отличаются services в GitHub Actions и GitLab CI?
11. Почему Locust не в Compose и почему swarm не бьёт в агент?
12. Чего не говорит p95 `GET /health` про `POST /agent/outreach`?
13. Почему видео на unlisted YouTube, а не в git?
14. Как честно сказать «35 дней» и «14 сжатых промптов»?
15. Почему нельзя постить ключи «для демо» и как мерить успех поста без vanity?
