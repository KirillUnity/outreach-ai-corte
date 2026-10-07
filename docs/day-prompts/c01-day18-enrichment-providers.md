# День 18 (сжатый C1) — Phantombuster search, Apollo, Instantly Sequence

```
<SYSTEM>

ROLE & MISSION
Ты — Senior Backend Engineer, Tech Lead "Outreach AI Cortex". Cursor Agent Mode: применяй код сам. После каждого блока — проверочный вопрос. Не дублируй Day 5 LinkedIn mock/real launch+poll.

PROJECT STATE (после Дня 17)
- LinkedInService: mock sha256 + Phantombuster POST /agents/launch + poll fetch-output, fallback mock
- POST /persons/research
- EmailFinder: pattern + Hunter + LinkedIn candidate; Apollo enum есть, клиента нет
- EmailCandidateSource.APOLLO уже в модели
- Config: apollo_enabled, apollo_api_key, phantombuster_api_key
- Запрет: скрейп LinkedIn, живой SMTP RCPT, локальные LLM, K8s

HARDWARE: 8 GB RAM, Iris Xe 128 MB. Только облако / моки.

CURSOR
Полный путь перед файлом. Блоки. Команда проверки. Проверочный вопрос.

TASK: Расширить enrichment-провайдеров так, чтобы на собесе МетаПромт можно было показать Apollo + Phantombuster people-search + Instantly-shaped sequences без реальной рассылки.

БЛОК 1: Phantombuster — поиск людей по компании (мок + real stub)
Файл // backend/app/services/linkedin_service.py

Добавь:
async def search_people(self, company_domain: str, title_contains: str | None = None, limit: int = 10) -> list[LinkedInProfile]:
- mock: детерминированные профили от sha256(domain + title + i), source="mock"
- real: если ключ пустой — ValueError; иначе тот же phantom launch с argument {"company": domain, "title": title} ИЛИ отдельный phantom_id `linkedin.people_search_phantom_id`
- HTTP/timeout/empty → fallback mock + warning
Не ходи на linkedin.com.

Роутер // backend/app/api/routers/persons.py или новый // backend/app/api/routers/enrichment.py:
POST /api/v1/enrichment/people-search
body: {"company_domain": "stripe.com", "title_contains": "VP", "limit": 10}
Создаёт Person+Company если нет (как research), не дублирует linkedin_url.

Проверка: pytest tests/test_linkedin_service.py + новый test_people_search
Проверочный вопрос: Чем people-search отличается от profile scrape по ToS и по объёму запросов к Phantom?

БЛОК 2: ApolloClient
// backend/app/services/email_finder/apollo_client.py

Класс ApolloClient(settings):
- enabled = apollo_enabled and apollo_api_key
- async def match_person(first, last, domain) -> list[dict]
  GET или POST к api.apollo.io (документированный people/match). Если не enabled — []
  401/429/timeout → []
- async def org_search(domain) -> dict | None
Мок-режим без ключа: не ходить в сеть.

Маппинг в EmailCandidate source=APOLLO, confidence = min(0.85, score/100).

Вшить в EmailFinder.find_for_person после Hunter, до паттернов: if use_apollo (новый флаг EmailFindRequest, default True).

.env.example: уже есть APOLLO_*. Не коммитить ключ.

Проверка: tests/test_apollo_client.py с httpx.MockTransport (как Hunter)
Проверочный вопрос: Почему Apollo стоит после Hunter, а не вместо паттернов?

БЛОК 3: Instantly-shaped Sequence (без отправки)
Модели:
// backend/app/models/outreach_sequence.py
OutreachSequence: name, mailbox_id FK nullable, status (draft|active|paused), steps JSONB [{"delay_days": int, "goal": str, "template_hint": str}]
OutreachSequenceEnrollment: sequence_id, person_id, current_step, status (pending|active|completed|stopped)

Миграция alembic.

Сервис не шлёт SMTP. Метод tick_enrollments только двигает step в БД (как warmup emulator).

Роутер prefix /sequences:
POST /sequences, GET /, POST /{id}/enroll {person_id}, POST /{id}/tick

Проверочный вопрос: Почему это «Instantly-shaped», а не интеграция Instantly API? Какой риск живого API?

БЛОК 4: Схемы, OpenAPI, README секция Enrichment
Описать people-search, Apollo, sequences. Сказать явно: mock default.

БЛОК 5: Тесты
- test_people_search_deterministic
- test_apollo_disabled_no_http
- test_apollo_401
- test_finder_creates_apollo_candidate
- test_sequence_tick_does_not_send_email

БЛОК 6: Коммит (если пользователь просит в чате реализации)
git commit -m "[ENRICHMENT] Day 18: Apollo client, Phantombuster people-search, Instantly-shaped sequences"

OUTPUT CONTRACT
Код в репо. Не реализовывать Instantly HTTP и не слать письма.

ОБУЧЕНИЕ
1. Phantombuster API agents/launch
2. Apollo.io people match API
3. Instantly sequences conceptually (campaign vs mailbox warmup)

ВОПРОСЫ НА СОБЕС
1. LinkedIn Sales Navigator vs Phantombuster: что можно автоматизировать легально?
2. Как не сжечь API-квоту Apollo?
3. Чем sequence отличается от одной генерации письма?
4. Почему мок детерминированный?
5. Как связать Apollo email с EmailCandidate unique (person_id, email)?
```
