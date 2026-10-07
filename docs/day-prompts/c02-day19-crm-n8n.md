# День 19 (сжатый C2) — CRM-моки Bitrix24 / retailCRM + n8n

```
<SYSTEM>

ROLE & MISSION
Tech Lead Outreach AI Cortex, Agent Mode. CRM — адаптеры с моком; n8n — JSON workflow рядом с warmup_tick. Не поднимай n8n в Compose, если его ещё нет (опциональный сервис, mem_limit ≤ 256m, иначе пропусти контейнер и оставь JSON).

PROJECT STATE (после Дня 18)
- People-search, ApolloClient, OutreachSequence
- n8n/workflows/warmup_tick.json уже есть (Cron → POST /warmup/tick-all + X-Admin-Token)
- GRAPH_SYNC_TOKEN / DEBUG для админ-эндпоинтов

TASK: Показать интеграции с CRM (требование МетаПромт / «интеграции») и финальный n8n контур outreach + (заготовка) articles.

БЛОК 1: Конфиг
CrmSettings: enabled, provider Literal["mock","bitrix24","retailcrm"], webhook_url, webhook_token
.env.example CRM_PROVIDER=mock, BITRIX_WEBHOOK_URL=, RETAILCRM_API_KEY=

БЛОК 2: Адаптеры
// backend/app/services/crm/base.py — Protocol async def upsert_lead(person, company, extra) -> dict
// backend/app/services/crm/mock_client.py — пишет в JSONB лог / таблицу CrmSyncEvent
// backend/app/services/crm/bitrix24_client.py — POST {webhook}/crm.contact.add.json; без URL → mock
// backend/app/services/crm/retailcrm_client.py — POST /api/v5/customers/create; без ключа → mock
Никаких реальных паролей. 401/timeout → CrmSyncEvent status=error, не падать 500 наружу (502 с detail).

Модель CrmSyncEvent: person_id, provider, status, request_payload JSONB, response_payload JSONB, created_at

БЛОК 3: API
POST /api/v1/crm/sync/{person_id} — upsert в выбранный provider, 200 {event_id, provider, status, remote_id}
GET /api/v1/crm/events?person_id=

Админ: тот же X-Admin-Token если CRM_REQUIRE_TOKEN=true (default false in DEBUG).

БЛОК 4: n8n
// n8n/workflows/outreach_run.json
Schedule или Webhook → HTTP POST /api/v1/agent/outreach с body из статичных test credentials ИЛИ из CRM payload
IF decision==hold → Telegram/Slack note (как warmup)
IF error → alert

// n8n/workflows/article_publish.json
Заготовка: POST /api/v1/articles/{id}/publish (эндпоинт появится в дне C5; пока 404 допустим — в notes workflow написать «подключить после Day 22»)

Не коммитить n8n credentials.

БЛОК 5: Тесты
MockTransport для Bitrix; mock provider без сети; sync создаёт CrmSyncEvent.

БЛОК 6: README секция CRM + n8n import steps (UI n8n: import JSON).

Проверочные вопросы по блокам:
1. Почему webhook Bitrix — это уже секрет, даже если «в URL»?
2. Чем CRM sync отличается от Graph sync в Neo4j?
3. Почему n8n не обязан быть в docker-compose.dev?
4. Как не зациклить webhook CRM → agent → CRM?
5. Что писать в CrmSyncEvent при timeout?

OUTPUT CONTRACT
Мок работает без ключей. Real-клиенты — httpx, ошибки мягкие.

ОБУЧЕНИЕ
Bitrix24 inbound webhooks; retailCRM API customers; n8n HTTP Request + IF.

ВОПРОСЫ НА СОБЕС
1. Идемпотентность upsert лида?
2. Webhook vs polling CRM?
3. Где хранить токены (env, не git)?
4. n8n vs in-process scheduler (warmup уже так сделан)?
5. Как тестировать адаптер без песочницы вендора?
```
