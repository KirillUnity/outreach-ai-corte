# Python для Kotlin-разработчика: Outreach AI Cortex

Гайд для человека с десятью годами Kotlin/Android (coroutines, Hilt, Retrofit, Room). Карта сервисов и запуск — в [how-it-works.ru.md](how-it-works.ru.md). Здесь — как читать **этот** репозиторий: `async def` вместо `suspend`, Pydantic вместо HTTP-`data class`, SQLAlchemy `Mapped` вместо Room, паттерны на месте. Стек: Python 3.12, FastAPI, Poetry; пакет `app` из `backend/` (`pyproject.toml`).

## Elevator (English, interviews)

Gradle maps to Poetry. Room entities are SQLAlchemy `Mapped`. HTTP DTOs are Pydantic v2, not the ORM.

Hilt `inject` is FastAPI `Depends` plus `get_settings` with `lru_cache`. `suspend` is `async def`; there is no `Dispatchers.IO`.

The event loop is the main thread. Blocking it is `runBlocking` on Android Main.

`EmailFinder` is a Facade. CRM is Adapter. `LLM_MODE` is Strategy. Articles and sequences are status machines. Guardrails run with `asyncio.gather`.

LangGraph is a coded `StateGraph`, not a free ReAct `AgentExecutor`. Generate always stores `draft`. Warmup `tick` never opens SMTP.

## 1. Таблица соответствий

| Kotlin | Python в Cortex |
|--------|-----------------|
| Gradle / модули | Poetry (`pyproject.toml`), пакет `app` из `backend/` |
| `data class` DTO | Pydantic v2 schema в `backend/app/schemas/` — **не** ORM |
| Entity Room | SQLAlchemy 2 `Mapped` в `backend/app/models/` |
| Hilt / Koin | FastAPI `Depends`, `get_settings` через `lru_cache` |
| `suspend fun` | `async def` + `await` (PEP 492) |
| `Dispatchers.IO` | отдельный диспетчер не нужен: event loop + `asyncpg` / `httpx` |
| `runBlocking` на Main | блокировать loop = плохо (как `runBlocking` на UI) |
| `coroutineScope` / `async` | `asyncio.gather` — **только** где IO независимый |
| `Result` / `runCatching` | `HTTPException` в роутере; в сервисах — исключения вроде `NotFoundError`, не тип `Result` |
| Retrofit interface | `httpx.AsyncClient` в Hunter / Apollo / CRM / webhook publish |
| `Flow` | **нет** как паттерн продукта; SSE в коде нет (`StreamingResponse` / `text/event-stream` не используются) |

Hilt-аналог — процессный синглтон настроек, как `@Singleton`:

```19:28:backend/app/api/deps.py
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session for a single request."""
    async for session in _get_db():
        yield session


@lru_cache
def get_settings() -> Settings:
    """Process-wide Settings. Parsing .env on every request is wasted work."""
    return Settings()
```

`get_db` ближе к `@ActivityRetained` / request-scoped: сессия на один HTTP-запрос, не на процесс.

**Честно про корутины и GIL.** High-load CPU и GIL здесь не оптимизировали: нет локальных LLM, PyTorch, numpy. Оптимизация = не блокировать loop, таймауты (`httpx`, LLM), ретраи (`RetryPolicy`), mock в CI (`LLM_MODE` / `RAG_MODE`). Sync `requests.get` / `time.sleep` / sync SQLAlchemy в `async def` — как `runBlocking` на UI: loop не отдаёт чужие запросы.

`asyncio.gather` — независимые рельсы `GuardrailPipeline`, не Hunter+Apollo: finder пишет в один `existing`-словарь последовательно. `gather` до upsert имел бы смысл, в коде его нет.

## 2. Два типа, не один data class

На Android часто один `data class` ездит и в Retrofit, и в Room (`@Entity` + `@Parcelize`). В Cortex граница жёсткая.

**Pydantic v2** — контракт HTTP: валидация входа, `Field`, нормализация домена, `response_model`. Это DTO.

```21:27:backend/app/schemas/article.py
class ArticleGenerateRequest(BaseModel):
    """Parameters for RAG-backed article generation."""

    company_domain: str = Field(min_length=3, max_length=255)
    keyword: str = Field(min_length=2, max_length=255)
    language: str = Field(default="ru", min_length=2, max_length=10)
    max_words: int = Field(default=800, ge=100, le=2000)
```

**SQLAlchemy 2 `Mapped`** — таблица Postgres, `select()`, `AsyncSession`. Это Room-entity. Ответ наружу собирается через `CompanyResponse.model_validate(company)` (`from_attributes=True`), а не отдачей ORM в JSON.

```19:31:backend/app/models/person.py
class Person(UUIDMixin, TimestampMixin, Base):
    """A contact at a company (or unaffiliated if company was deleted)."""

    __tablename__ = "persons"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    linkedin_url: Mapped[str | None] = mapped_column(
        String(500),
        unique=True,
        nullable=True,
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

Запросы — SQLAlchemy 2 `select(EmailCandidate).where(...)`, не legacy `Query`. Смешать schema и model в один класс нельзя: HTTP начнёт знать FK/CASCADE, а таблица — `max_words` и `pattern` слага.

## 3. Ключевые методы

### `EmailFinder.find_for_person` — Facade

Файл: `backend/app/services/email_finder/finder.py`.

```35:42:backend/app/services/email_finder/finder.py
    async def find_for_person(
        self,
        person: Person,
        domain: str | None = None,
        use_hunter: bool = True,
        use_smtp: bool = False,
        use_apollo: bool = True,
    ) -> list[EmailCandidate]:
```

**Зачем.** Один вход: LinkedIn-email персоны + опционально Hunter + Apollo + pattern guesses (`first.last`, `flast`, …). Upsert в память, затем commit. Уникальность `person_id + email` — `UniqueConstraint` `uq_email_candidates_person_email`. SMTP по умолчанию выкл: агент передаёт `use_smtp=False`; `SMTPVerifier` при `SMTP_VERIFICATION_ENABLED=false` не открывает MX, возвращает `unknown`.

**Кто зовёт.** `POST /api/v1/email/find` (`email_finder` router) и нода `find_email_node` в LangGraph (`OutreachAgentService` собирает `EmailFinder` на запрос). Нет ящика — generate всё равно идёт.

### `build_outreach_graph` — политика в коде, не AgentExecutor

Файл: `backend/app/services/agent/graph.py`.

```50:60:backend/app/services/agent/graph.py
def build_outreach_graph(
    person_service: PersonService,
    company_service: CompanyService,
    rag_service: RAGService,
    email_generator: EmailGenerator,
    validator: OutputValidator,
    deliverability_checker: DeliverabilityChecker,
    draft_service: EmailDraftService,
    settings: Settings,
    *,
```

Keyword-args дальше: `guardrail_pipeline`, `email_finder`, Neo4j-сервисы. **Зачем.** Собирает `StateGraph(OutreachState)`: load → research → RAG → enrich_with_graph → find_email → generate → validate → deliverability → decide → save_draft / save_and_send. Рёбра в `edges.py` — обычные функции, не tool-calling LLM. Ребро `find_email → generate_email` безусловное. `decide` читает `AGENT_REQUIRE_HUMAN_APPROVAL` (dev: hold). Это **не** LangChain `AgentExecutor` / свободный ReAct.

**Кто зовёт.** `OutreachAgentService._build_graph` → `run` → `POST /api/v1/agent/outreach`.

### `ArticleGenerator.generate` — всегда draft

Файл: `backend/app/services/article_generator.py`.

```87:100:backend/app/services/article_generator.py
        article = SEOArticle(
            company_id=company.id,
            title=title,
            slug=slug,
            body_markdown=body,
            language=request.language,
            status="draft",
            keywords=[],
            rag_context_used=hits,
            tokens_input=int(result["tokens_input"]),
            tokens_output=int(result["tokens_output"]),
            estimated_cost_usd=record.estimated_cost_usd if record else 0,
            generation_prompt_version=ARTICLE_PROMPT_VERSION,
            keyword_primary=request.keyword,
        )
```

Сигнатура: `async def generate(self, request: ArticleGenerateRequest) -> SEOArticle`. RAG по домену + `LLMClient.chat_json`, валидация title/slug/body, запрет URL-shortener. Публикации нет.

**Кто зовёт.** `POST /api/v1/articles/generate`. Optimize / schedule / publish — другие классы.

### CRM `upsert_lead` — Adapter

Файлы: `backend/app/services/crm/` (`base.py`, `mock_client.py`, `bitrix24_client.py`, `retailcrm_client.py`).

```11:21:backend/app/services/crm/base.py
class CrmClient(Protocol):
    provider_name: str

    async def upsert_lead(
        self,
        person: Person,
        company: Company | None,
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        """Return {status: ok|error, remote_id, raw, request}."""
        ...
```

**Зачем.** Один контракт: mock / Bitrix `crm.contact.add.json` / retailCRM `customers/create`. `CrmService.build_client()` выбирает адаптер из `CRM_PROVIDER`; пустые креды → mock. HTTP — `httpx.AsyncClient` с timeout.

**Кто зовёт.** `CrmService.sync_person` → `POST /api/v1/crm/sync/{person_id}`. Роутер провайдера не знает.

### `WarmupEmulator.tick` — не SMTP

Файл: `backend/app/services/warmup/warmup_emulator.py`.

```66:79:backend/app/services/warmup/warmup_emulator.py
    async def tick(self, mailbox_id: UUID) -> int:
        mailbox = await self._get_mailbox(mailbox_id)
        if mailbox.status in {MailboxStatus.PAUSED, MailboxStatus.BANNED}:
            return 0
        if mailbox.status == MailboxStatus.NEW:
            mailbox.status = MailboxStatus.WARMING
            mailbox.warmup_started_at = mailbox.warmup_started_at or datetime.now(timezone.utc)
            if mailbox.warmup_day < 1:
                mailbox.warmup_day = 1
        day = mailbox.warmup_day if mailbox.warmup_day >= 1 else 1
        mailbox.warmup_day = day
        limit = self._limit_for_day(day)
        mailbox.daily_limit = limit
        send_count = min(limit, self.settings.warmup.max_emails_per_tick)
```

**Зачем.** Один tick = один симулированный день: `WarmupEvent` против `PeerNetwork`, репутация, NEW→WARMING→WARMED/BANNED. Писем в интернет нет.

**Кто зовёт.** `WarmupService.run_tick` → `POST /warmup/mailboxes/{id}/tick`; `tick_all` → `POST /warmup/tick-all`.

## 4. Паттерны по месту

**Adapter — CRM.** `CrmClient` Protocol + три клиента. Роутер вызывает `CrmService`, не Bitrix URL. Как Retrofit-интерфейс с разными backend-ами, только без кодогена.

**Strategy — `LLM_MODE`.** `LLMClient.chat`: `mock` и нет клиента → детерминированный ответ без сети; `real` → `AsyncOpenAI` + `RetryPolicy`. То же семейство: `RAG_MODE`, `LINKEDIN_MODE`. CI без ключей — стратегия mock, не «быстрее корутины».

**State machine — статьи и sequences.** Статья: generate всегда `draft` → optimize (мета, статус часто остаётся draft) → `scheduled` → `published` / `failed`. Publish идемпотентен. Sequence: `DRAFT|ACTIVE|PAUSED`; enrollment `PENDING → ACTIVE → COMPLETED`; `tick` только `current_step++`, `emails_sent` всегда 0. Mailbox warmup — ещё один enum-граф (`NEW/WARMING/WARMED/PAUSED/BANNED`).

**Pipeline — `GuardrailPipeline`.** Hallucination, content policy, PII, structure. Независимый IO (и CPU-лёгкие regex) — как structured concurrency:

```26:36:backend/app/services/guardrails/pipeline.py
    async def run_all(
        self, content: str, context: dict[str, Any] | None = None
    ) -> tuple[bool, list[GuardrailResult]]:
        ctx = context or {}
        raw = await asyncio.gather(
            *(self._safe_check(rail, content, ctx) for rail in self.guardrails),
            return_exceptions=False,
        )
        results = list(raw)
        all_passed = not any((not item.passed) and item.severity in _BLOCKING for item in results)
        return all_passed, results
```

Упал один рельс — `error`-результат, не 500. Warnings не блокируют. Нода `validate_email` может один раз вернуть на generate.

**Facade — `EmailFinder`.** Роутер не знает Hunter URL и список паттернов. Finder прячет клиентов и `_upsert`.

**DI — `Depends`.** Как Hilt `@Inject` на параметре: `db: AsyncSession = Depends(get_db)`, `settings: Settings = Depends(get_settings)`. Тест подменяет dependency — аналог fake-модуля Hilt.

## 5. SOLID / DRY / KISS — только наблюдения

**S.** Хороший тонкий роутер: `research_company` проверяет 404, ловит сбой сервиса в 502, отдаёт DTO. Парсер (httpx + trafilatura) и Chroma остаются в `CompanyService.research`.

```109:119:backend/app/api/routers/companies.py
    service = _service(db)
    existing = await service.get_by_domain(domain)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company '{domain}' not found",
        )

    start = time.perf_counter()
    try:
        company, parsed, chunks_indexed = await service.research(domain)
```

Риск: `backend/app/api/routers/graph.py` — длинный HTTP-слой с хелперами `_node` / `_as_uuid` и сборкой Warm Intro DTO из словарей Neo4j. Это ещё не парсер в роутере, но SRP уже тянется: маппинг графа живёт рядом со статусами, не в сервисе.

**O.** Новый CRM: класс с `upsert_lead` + ветка в `CrmService.build_client`. Роутер `crm.py` не трогаем — OCP на HTTP-границе соблюдён. Фабрика всё же правится (нет registry/entry-point). Для портфолио из трёх провайдеров это нормальный KISS.

**D.** URL и ключи — `Settings` / nested `crm`, `llm`, `email_finder`, не хардкод в клиентах. Hunter берёт `hunter_base_url` из настроек. Bitrix webhook — env, не git.

**DRY.** `Bitrix24Client._post` и `RetailCrmClient._post` почти копии (timeout, 401/403). Smell: да. Осознанный: тела и auth разные. Для двух адаптеров дубль — допустимый KISS.

**KISS.** `StateGraph` с именованными нодами проще свободного ReAct: политика «нет email ≠ стоп generate», «hold по флагу», «один regenerate» — в `edges.py`, её можно прочитать на собесе без трейса tool-calls. `AgentExecutor` спрятал бы это в промпт.

## Проверочные вопросы

1. **Почему Pydantic и SQLAlchemy — два типа, не один data class?** HTTP-контракт (валидация, примеры, `max_words`) и таблица (FK, enum, unique) живут разный срок жизни. Room+Moshi иногда совмещают; здесь `ArticleGenerateRequest` не знает `seo_articles.status`, а `SEOArticle` не валидирует keyword length на границе API.

2. **Чем `async def` в FastAPI отличается от `suspend` на Android Main?** Оба — кооперативная отмена точки `await`. FastAPI крутит **один** event loop на процесс (uvicorn worker). Это Main-thread приложения: `await httpx` отпускает loop, `requests.get` — нет. На Android `suspend` с `Dispatchers.IO` уводит IO с Main; отдельного IO-диспетчера в Cortex нет — IO должен быть async (`asyncpg`, `httpx`).

3. **Зачем mock LLM, если «корутины ускоряют»?** Корутины не ускоряют CPU и не заменяют ключ OpenAI. Mock — стратегия для CI и демо на 8 ГБ без токенов. `gather` не сделает `gpt-4o-mini` бесплатным.

4. **Где аналог structured concurrency?** `asyncio.gather` в `GuardrailPipeline.run_all`: параллельные независимые проверки, сбой рельса изолирован. Finder **не** structured concurrency: источники идут по очереди из-за общего upsert. `coroutineScope` на каждый HTTP-запрос ≈ lifespan `await` до ответа; cancellation клиента FastAPI не моделирует как `viewModelScope`.

5. **Что будет, если в async route вызвать sync `requests.get`?** Заблокируется event loop worker'а: health и чужие запросы ждут сокет. Это `runBlocking` на UI. Нужен `httpx.AsyncClient` (Hunter/CRM); thread pool для HTTP в репо не используется.
