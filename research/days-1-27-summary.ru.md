# Outreach AI Cortex — канонические итоги дней 1–27

English: [days-1-27-summary.en.md](days-1-27-summary.en.md). Исторические срезы:
[1–20](days-1-20-summary.ru.md), [1–12](days-1-12-summary.ru.md) и
[1–8](days-1-8-summary.ru.md).

## Архитектура

Python 3.12, FastAPI, async SQLAlchemy 2.0, PostgreSQL 16, ChromaDB, Neo4j,
React/Vite, Poetry и Docker Compose. Продовые LLM/embedding-вызовы идут только в облачные API;
mock-режимы делают локальную разработку и CI детерминированными. Postgres — источник CRUD-данных,
Chroma — RAG-чанки компаний, Neo4j — индекс связей и путей.

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
  опциональный единичный LLM-вызов и кнопка Optimize.
- День 26: сфокусированные backend-тесты, SMTP-disabled/duplicate/empty-result ветки, Vitest UI и
  [инструкция по тестам](../docs/TESTING.md).
- День 27: GitHub Actions и GitLab CI с PostgreSQL 16, mock-режимами, backend/frontend
  тестами и build без deploy.

## Жизненный цикл статьи

`Company.raw_site_text → Chroma retrieval → версионированный JSON prompt →
SEOArticle(draft) → review/optimize → scheduled → admin tick → mock или webhook publish`.

Generate никогда не публикует автоматически. Mock URL использует `example.invalid`; ошибка
webhook переводит статью в failed. Internal links ограничены доменом компании и путями сохранённых
статей. Повторный publish — no-op.

## Проверка

```bash
poetry run pytest -q
poetry run pytest --cov=app --cov-report=term-missing --cov-fail-under=0
cd frontend && npm ci && npm test && npm run build
docker compose exec api poetry run alembic upgrade head
```

CI использует Python 3.12, Node 20 и PostgreSQL 16. Chroma, Neo4j, Langfuse и весь Compose там не
стартуют. Секреты внешних сервисов не требуются.

## Самопроверка / собеседование

1. Почему статья относится к Company, а не Person?
2. Почему JSON от LLM безопаснее сырого markdown?
3. Как RAG и editorial disclaimer уменьшают риск галлюцинаций?
4. Почему generate заканчивается статусом draft и кто утверждает публикацию?
5. Как status transition и идемпотентность защищают от дублей?
6. Почему LLM-SEO выключен по умолчанию?
7. Зачем ограничивать длину meta и число внутренних ссылок?
8. Почему 70% для новых пакетов лучше, чем 80% для всего legacy?
9. Зачем CI mock-режимы и настоящий PostgreSQL service?
10. Чем отличаются services в GitHub Actions и GitLab CI?
