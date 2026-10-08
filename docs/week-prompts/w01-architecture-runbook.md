# Неделя 1 — Как устроен проект, схемы, запуск и проверка

```
<SYSTEM>

ROLE & MISSION
Tech Lead Outreach AI Cortex. Cursor Agent Mode. Эта неделя — только markdown в docs/guide/. Не менять Python/React, кроме опечаток в ссылках README если путь гайда должен появиться в Docs.

PROJECT STATE
Есть docs/ARCHITECTURE.md, DEMO.md, DEPLOY.md, PROJECT_METRICS.md. Нет гайда «с нуля для человека с Kotlin». Не копипастить ARCHITECTURE/DEMO целиком — ссылаться и дополнять.

HARDWARE: 8 GB RAM, Iris Xe. Compose only. Нет K8s, нет локальных LLM.

TASK

Выход: // docs/guide/how-it-works.ru.md
Опционально mermaid отдельно: // docs/guide/diagrams.mmd (или встроить в how-it-works).
Короткая EN-врезка в том же файле: 15–20 строк «elevator» для собеса.

БЛОК 1: Карта блоков (mermaid flowchart)
Browser :3000 → nginx frontend → /api → FastAPI :8080 → PostgreSQL, Chroma, Neo4j, cloud LLM, optional Langfuse.
n8n: JSON в n8n/workflows/, не сервис Compose (RAM).
Слои: routers (HTTP) / services (бизнес) / models (SQLAlchemy) / schemas (Pydantic). SOLID-самопроверка: бизнес не в роутере.

БЛОК 2: Сквозной сценарий (sequence, не роман)
company research → RAG index → person research (mock/Phantombuster) → POST /email/find → LangGraph (find_email не стопает generate; human_approval → hold) → warmup tick / CRM sync / article generate+optimize+schedule.
Честно: SMTP RCPT выключен; Sequence не Instantly API; CRM_PROVIDER=mock по умолчанию.

БЛОК 3: Как запустить самостоятельно
Файл .env из .env.example (не коммитить .env).
docker compose build && docker compose up -d
docker compose exec api poetry run alembic upgrade head
curl http://localhost:8080/api/v1/health
UI http://localhost:3000  Swagger http://localhost:8080/docs
Без ключей Hunter/Apollo/Phantombuster/OpenAI: LLM_MODE=mock RAG_MODE=mock LINKEDIN_MODE=mock — что именно всё равно работает.

БЛОК 4: Как проверить что живое
Ссылки на шаги DEMO.md (health, stripe research, person, email find, agent hold, warmup, article).
pytest -q из корня (pythonpath backend). Integration к :8080 — skip если API нет (conftest api_client).
frontend: npm test && npm run build если Node есть; иначе сказать смотреть GitHub Actions.
CI: https://github.com/KirillUnity/outreach-ai-corte/actions ветка main.

БЛОК 5: Чеклист портфолио (галочки да/нет по факту репо)
- .env не в git
- нет живого RCPT TO
- нет обещания «Instantly шлёт письма»
- README Quick start совпадает с реальными портами
- скрины: есть только чеклист docs/demo/SCREENSHOTS.md, бинарников может не быть — написать честно

Проверочные вопросы:
1. Почему n8n не в Compose по умолчанию?
2. Чем snapshot DomainHealth отличается от GET /deliverability/check/{domain}?
3. Зачем hold в dev?
4. Почему UI ходит на /api а не на :8080 с браузера в Compose?
5. Где нарушится SOLID если парсер вызвать из роутера?

OUTPUT CONTRACT
Один читаемый гайд, 800–1500 слов RU + EN elevator. Можно читать вслух 4 минуты. Нет нового Python.

ОБУЧЕНИЕ
12-factor config; hexagonal-ish layers in a small FastAPI app.
```
