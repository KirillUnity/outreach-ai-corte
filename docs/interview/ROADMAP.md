# Подготовка к собесам — roadmap

Для Кирилла Соколова. Код: [Outreach AI Cortex](https://github.com/KirillUnity/outreach-ai-corte).  
Сводка продукта: [дни 1–20 RU](../../research/days-1-20-summary.ru.md) · [EN](../../research/days-1-20-summary.en.md).  
**Красная линия:** коммерческий Python = РИАЦ + Cortex, не «4 года микросервисов». Kafka / Redis / Kubernetes в проде **не было**. Docker Compose — да. Локальных LLM нет (8 GB RAM).

Письма откликов не дублируем — только ссылки. Этот файл не заменяет день-34 `ANSWERS.md`.

---

## 1. Карта вакансий

| Вакансия | Отклик | Что зубрить в первую очередь | Чего не врать |
|----------|--------|------------------------------|----------------|
| FastAPI / PostgreSQL | [docs/otklik-python-fastapi.md](../otklik-python-fastapi.md) | FastAPI, Pydantic v2, SQLAlchemy 2 `select()`, Alembic, pytest, OpenAPI, Compose | GitLab CI — пока нет YAML (промпт C8); Django нет |
| FastAPI / агенты | [docs/otklik-fastapi-agents.md](../otklik-fastapi-agents.md) | LangGraph, промпты, RAG, Neo4j, Langfuse, оценка рисков API | Redis, брокер, GIL/high-load прод, Prometheus как стек |
| Python аутстафф | [docs/otklik-python-outstaff.md](../otklik-python-outstaff.md) | Cortex как демо LLM/RAG + честный стаж | Kafka, K8s, «4 года Python senior» |
| Скрининг ИП 2000 ₽/ч | [docs/otklik-screening-ip.md](../otklik-screening-ip.md) | 2-минутный питч, ставка, ИП, окно 8/5 заказчика | Двойной фуллтайм в резюме |
| Chatix (боты в продажах) | [docs/otklik-chatix.md](../otklik-chatix.md) | Промпт, тон, CTA, «бот плывёт» = guardrails | Опыт платформы Chatix |
| Солвиум junior (тележки) | [docs/otklik-solvium-junior.md](../otklik-solvium-junior.md) | Спека→API, SQL, тесты, Tortoise vs SQLAlchemy | Senior Python; домен роботов «я уже делал парк» |
| МетаПромт / КиберСтатьи | [docs/day-prompts/README.md](../day-prompts/README.md) | Apollo/Phantombuster/n8n/sequence — **мок vs real** | Живой SMTP, скрейп LinkedIn, Instantly-рассылка |

Ближайший созвон: дорожка **A** (все) + **B** если агенты + **D** если Солвиум + **E** если Chatix.

---

## 2. Схема учёбы

```mermaid
flowchart TB
  core[A_FastAPI_SQLAlchemy_Postgres]
  tests[A2_pytest_httpx_mocks]
  docker[A3_Compose_not_K8s]
  rag[B_RAG_Chroma_cloudLLM]
  agent[B2_LangGraph_guardrails]
  obs[B3_Langfuse]
  graph[C_Neo4j_warm_intro]
  email[C2_finder_deliverability_warmup]
  junior[D_SQL_Tortoise_spec_API]
  sales[E_prompts_Chatix]
  core --> tests --> docker
  rag --> agent --> obs
  graph --> email
  docker --> junior
  agent --> sales
```

Три параллельных трека по ~2 недели. Если собес завтра: 1 день A (карточки 1–3) + питч из раздела 6.

---

## 3. Дорожки (что открыть в репо)

### A — FastAPI / SQL / тесты / Compose (вакансии FastAPI, аутстафф, junior)

| День | Тема | В репо | Статьи |
|------|------|--------|--------|
| A1 | Слои, Depends, Pydantic | [backend/app/main.py](../../backend/app/main.py), [backend/app/api/deps.py](../../backend/app/api/deps.py), любой router в `backend/app/api/routers/` | [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/), [Pydantic v2](https://docs.pydantic.dev/latest/) |
| A2 | SQLAlchemy 2 async, Alembic | [backend/app/models/](../../backend/app/models/), [backend/app/core/database.py](../../backend/app/core/database.py), `alembic/versions/` | [SQLAlchemy 2.0 SELECT](https://docs.sqlalchemy.org/en/20/tutorial/data.html#selecting-rows-with-core-or-orm) |
| A3 | pytest, httpx mock | [backend/tests/test_hunter_client.py](../../backend/tests/test_hunter_client.py), [backend/tests/test_apollo_client.py](../../backend/tests/test_apollo_client.py) | [httpx MockTransport](https://www.python-httpx.org/advanced/transports/) |
| A4 | Compose, RAM, не K8s | `docker-compose.yml`, [docs/ARCHITECTURE.md](../ARCHITECTURE.md) | Compose healthcheck (докер docs); **не** учить Helm |
| A5 | CI как пробел | честно: YAML ещё в промпте [c08](../day-prompts/c08-day27-cicd.md) | [GitLab CI YAML](https://docs.gitlab.com/ee/ci/yaml/) — прочитать jobs/stages, не врать «я настраивал прод» |

Итоги дней: [research/days-1-5-summary.ru.md](../../research/days-1-5-summary.ru.md).

### B — RAG, агент, Langfuse (агенты / аутстафф)

| День | Тема | В репо | Статьи |
|------|------|--------|--------|
| B1 | RAG, mock embeddings | `backend/app/services/rag_service.py`, splitter | [research/llm-prompt-engineering-for-outreach.md](../../research/llm-prompt-engineering-for-outreach.md) |
| B2 | LLMClient mock/real | `backend/app/services/llm_client.py`, `email_generator.py` | OpenAI chat JSON mode (офиц. docs) |
| B3 | LangGraph | [backend/app/services/agent/graph.py](../../backend/app/services/agent/graph.py), [docs/agent_graph.mmd](../agent_graph.mmd) | [LangGraph StateGraph](https://langchain-ai.github.io/langgraph/), [research/langgraph-vs-langchain-agents.md](../../research/langgraph-vs-langchain-agents.md) |
| B4 | Guardrails, hold | `backend/app/services/guardrails/`, `nodes.py` decide | [PROMPTS.md](../../PROMPTS.md) |
| B5 | Langfuse | tracing service | [research/langfuse-observability-for-llm.md](../../research/langfuse-observability-for-llm.md) |

Шпаргалка: [research/days-1-8-summary.ru.md](../../research/days-1-8-summary.ru.md), [research/days-1-12-summary.ru.md](../../research/days-1-12-summary.ru.md).

### C — Граф и почта (МетаПромт, агенты)

| День | Тема | В репо | Статьи |
|------|------|--------|--------|
| C1 | Neo4j vs PG | `backend/app/services/graph/` | [research/neo4j-vs-postgresql-graph-queries.md](../../research/neo4j-vs-postgresql-graph-queries.md), [research/warm-intro-path-finding.md](../../research/warm-intro-path-finding.md) |
| C2 | Email finder | `backend/app/services/email_finder/` | [research/email-finding-strategies.md](../../research/email-finding-strategies.md) |
| C3 | SMTP-риск, catch-all | `smtp_verifier.py` — **мок** | ZeroBounce/SMTP verification risks (блог, концепт) |
| C4 | SPF/DKIM/DMARC | `backend/app/services/deliverability/` | [research/email-deliverability-2024.md](../../research/email-deliverability-2024.md), [RFC 7208 SPF](https://datatracker.ietf.org/doc/html/rfc7208) (обзор, не наизусть) |
| C5 | Warmup emulator, sequences | warmup + `sequence_service.py` | [research/warmup-mechanics.md](../../research/warmup-mechanics.md); n8n HTTP Request node docs |

Day 18 в коде: people-search мок, Apollo без ключа не ходит в сеть, sequence **не шлёт** почту. LinkedIn: [research/linkedin-mock-vs-real.md](../../research/linkedin-mock-vs-real.md).

### D — Солвиум junior (спека, SQL, Tortoise)

| День | Тема | В репо | Статьи |
|------|------|--------|--------|
| D1 | Спека → thin router | любой `routers/*.py` vs `services/*_service.py` | FastAPI path operations |
| D2 | SQL глазами | JOIN person–company в голове; `selectinload` | Postgres JOIN / indexes (tutorial) |
| D3 | Tortoise vs SQLAlchemy | честно: в Cortex SQLAlchemy 2 | [Tortoise ORM](https://tortoise.github.io/) Why + models; сравнение с SQLAlchemy в 1 страницу своих слов |
| D4 | Дефект: воспроизвести → тест → правка | любой failing-test стиль в `backend/tests/` | — |

Не учить ROS/PLC. Интеграция «API вендора» = httpx + таймаут + мок, как Hunter/Apollo.

### E — Chatix / промпты

| День | Тема | В репо | Статьи |
|------|------|--------|--------|
| E1 | Почему письмо плохое | OutputValidator, spam words | [PROMPTS.md](../../PROMPTS.md) |
| E2 | Бот плывёт | длина, CTA, оффер, retry suffix | prompt engineering notes в research |
| E3 | Не продукт Chatix | отклик честный | — |

### Скрининг ИП

Перечитать [docs/otklik-screening-ip.md](../otklik-screening-ip.md). Питч 90 секунд: Cortex (FastAPI, PG, агент, GitHub) → РИАЦ SQL/REST → 10 лет Android не как Python-сеньор → 2000 ₽/ч, ИП, календарь заказчика.

---

## 4. Внешние статьи (короткий список)

| Тема | Зачем |
|------|--------|
| FastAPI Dependencies | Depends, слои, не бизнес-логика в router |
| Pydantic v2 models | схемы vs ORM |
| SQLAlchemy 2.0 selecting rows | `select()`, не legacy Query |
| Tortoise ORM docs | только Солвиум |
| LangGraph StateGraph | ноды, edges, state |
| Langfuse docs tracing | чем traces лучше «лога токенов» |
| SPF / DKIM / DMARC primer | deliverability без своего RCPT |
| SMTP verification risks | почему мок в Cortex |
| GitLab CI YAML | собес FastAPI; «читал, в репо ещё нет» если C8 не делали |
| n8n HTTP Request | МетаПромт; у нас JSON warmup tick |
| httpx transports | как мокать Hunter/Apollo |

Не тратить неделю на Kubernetes official curriculum.

---

## 5. Экзаменационные карточки

Формат: **Q** → **A** → *Cortex*.

### 5.1 FastAPI / Pydantic / слои

1. **Q:** Где бизнес-логика?  
   **A:** В `services/`, router — статус-коды и Depends.  
   *Cortex: `email_finder.py` router vs `EmailFinder`.*

2. **Q:** Зачем Pydantic отдельно от ORM?  
   **A:** Контракт HTTP ≠ таблица; validation на входе.  
   *Схемы в `app/schemas/`.*

3. **Q:** Почему `/api/v1`?  
   **A:** Версионирование публичного API.  
   *`main.py` include_router prefix.*

4. **Q:** FastAPI vs Django на этой вакансии?  
   **A:** Вакансия FastAPI; Django в проде не было.  
   *Честно в отклике.*

5. **Q:** Что даёт OpenAPI из коробки?  
   **A:** `/docs`, контракт для фронта и n8n.  
   *Swagger :8080/docs.*

6. **Q:** `get_settings` через lru_cache?  
   **A:** Не парсить `.env` на каждый запрос.  
   *`app/api/deps.py`.*

7. **Q:** 404 vs 409?  
   **A:** Нет сущности vs конфликт unique.  
   *`NotFoundError` / `DuplicateError`.*

8. **Q:** Async route без async БД?  
   **A:** Бессмысленно блокировать event loop sync SQL.  
   *AsyncSession везде в новом коде.*

### 5.2 SQLAlchemy 2 / Alembic / SQL

9. **Q:** Чем `select()` лучше Query API?  
   **A:** 2.0 style, явный SQL, typing.  
   *Все сервисы: `select(Person).where(...)`.*

10. **Q:** Зачем Alembic async?  
    **A:** Тот же Postgres, ревизии в git.  
    *`backend/alembic/versions/`.*

11. **Q:** ON DELETE CASCADE на drafts?  
    **A:** Черновики без персоны не живут.  
    *FK person_id.*

12. **Q:** Unique `(person_id, email)` на candidates?  
    **A:** Не плодить одну гипотезу дважды.  
    *EmailCandidate.*

13. **Q:** `selectinload` зачем?  
    **A:** Не N+1 person.company.  
    *`get_with_company`.*

14. **Q:** Индекс на `person_id`?  
    **A:** Частый фильтр списков.  
    *email_candidates, enrollments.*

15. **Q:** Транзакция find_for_person?  
    **A:** Один commit после upsert+primary.  
    *`EmailFinder`.*

16. **Q:** JSONB для чего?  
    **A:** Сырой ответ провайдера, generation_context.  
    *Не для поиска по всем ключам без GIN — знать ограничение.*

### 5.3 Тесты и моки

17. **Q:** Как тестировать Hunter без ключа?  
    **A:** `httpx.MockTransport`, 401/429 → `[]`.  
    *`test_hunter_client.py`.*

18. **Q:** Почему mock LinkedIn от hash, не random?  
    **A:** Детерминизм тестов и повторный research.  
    *`linkedin_service` sha256.*

19. **Q:** `LLM_MODE=mock` в CI?  
    **A:** Нет токенов, нет сети к OpenAI.  
    *Настройки llm.*

20. **Q:** Integration vs unit?  
    **A:** Unit без Postgres; HTTP к :8080 — только если контейнер жив.  
    *pytest в `backend/tests/`.*

21. **Q:** Что не мокать?  
    **A:** Валидацию Pydantic, чистые функции паттернов.  
    *`test_pattern_generator.py`.*

### 5.4 Docker / RAM

22. **Q:** Почему не Kubernetes?  
    **A:** Один хост 8 GB, Compose, правило проекта.  
    *`.cursorrules`.*

23. **Q:** Почему не Ollama?  
    **A:** Iris Xe 128 MB, RAM.  
    *Только облако / mock.*

24. **Q:** mem_limit?  
    **A:** Не дать Neo4j/Langfuse съесть машину.  
    *Compose services.*

25. **Q:** Postgres порт на 0.0.0.0 в prod?  
    **A:** Нельзя; только внутренняя сеть.  
    *Промпт C9 DEPLOY.*

26. **Q:** Healthcheck + depends_on?  
    **A:** API не стартует раньше живого PG.  
    *compose.*

### 5.5 RAG и LLM

27. **Q:** Что в чанке?  
    **A:** Кусок `raw_site_text` после splitter.  
    *RAGService collection `company_{domain}`.*

28. **Q:** mock embeddings?  
    **A:** Хэш-вектор, не нейросеть локально.  
    *`RAG_MODE=mock`.*

29. **Q:** Зачем top_k?  
    **A:** Не запихивать весь сайт в промпт.  
    *Стоимость и галлюцинации.*

30. **Q:** JSON subject/body?  
    **A:** Парсинг без markdown-обёртки.  
    *EmailGenerator + validator.*

31. **Q:** Retry генерации?  
    **A:** Валидатор/spam/guardrail → suffix в user prompt, второй вызов.  
    *`email_generator.py`.*

### 5.6 LangGraph / guardrails

32. **Q:** Чем граф лучше одного generate-email?  
    **A:** research → RAG → find_email → validate → deliverability → decide → save.  
    *`graph.py`, mermaid в README.*

33. **Q:** `require_human_approval=true`?  
    **A:** Чистый драфт всё равно **hold**, нет автоSMTP.  
    *AgentSettings / decide node.*

34. **Q:** Reducer `add` на errors?  
    **A:** Ошибки копятся; validation_errors — overwrite.  
    *`state.py`.*

35. **Q:** find_email не стопает граф?  
    **A:** Нет ящика → `email_found=false`, письмо всё равно для review.  
    *`find_email_node`.*

36. **Q:** Guardrail vs OutputValidator?  
    **A:** Validator — длина/spam-слова; rails — PII, policy, structure.  
    *pipeline + decide reject.*

37. **Q:** Checkpointer зачем?  
    **A:** Возобновление; в тестах MemorySaver.  
    *Не путать с Postgres checkpointer таблицы в prod.*

### 5.7 Neo4j / warm intro

38. **Q:** Зачем Neo4j если есть Postgres?  
    **A:** Пути и mutuals удобнее Cypher; PG — source of truth CRUD.  
    *research neo4j-vs-postgresql.*

39. **Q:** Warm intro?  
    **A:** Путь к человеку в компании без EmailThread.  
    *API graph/warm-intro/search.*

40. **Q:** Influence?  
    **A:** Эвристика по степеням связей, не PageRank Google.  
    *influence endpoint + UI badge.*

41. **Q:** Sync?  
    **A:** `X-Admin-Token`, `NEO4J_AUTO_SYNC_ON_WRITE=false` по умолчанию.  
    *Не открывать Bolt из каждого CRUD-теста.*

### 5.8 Email finder / catch-all / SMTP

42. **Q:** Несколько candidates?  
    **A:** Гипотезы с разных источников; primary — рабочий.  
    *Day 17.*

43. **Q:** `{first}.{last}` confidence 0.85?  
    **A:** Эмпирика паттернов, не вероятность из вашей БД.  
    *PatternGenerator.*

44. **Q:** Почему не живой RCPT TO?  
    **A:** Спам-разведка, блок IP.  
    *SMTPVerifier mock.*

45. **Q:** Catch-all?  
    **A:** MX принимает всё; SMTP бесполезен; confidence режем.  
    *email-finding-strategies.md.*

46. **Q:** Hunter vs Apollo vs pattern?  
    **A:** Hunter email-finder; Apollo match cap 0.85; pattern всегда.  
    *Порядок в `find_for_person`.*

47. **Q:** Unique person+email?  
    **A:** Upsert, не дубль.  
    *Day 17 constraint.*

48. **Q:** People-search vs scrape профиля?  
    **A:** Пачка по домену vs один `/in/`; оба не ходят на linkedin.com из нашего кода.  
    *Day 18 `search_people`.*

### 5.9 Deliverability / warmup / sequences

49. **Q:** Snapshot vs live DNS?  
    **A:** Агент смотрит DomainHealth в PG; live — `GET /deliverability/check/{domain}`.  
    *Два checker-класса, не путать.*

50. **Q:** Warmup emulator?  
    **A:** Фейковые peer-события, **нет SMTP**.  
    *Mailbox + WarmupEvent, n8n tick-all.*

51. **Q:** Sequence tick?  
    **A:** `current_step++`, `emails_sent=0`. Не Instantly API.  
    *`SequenceService`.*

52. **Q:** Open rate в 2024?  
    **A:** Apple MPP портит opens; лучше bounce/complaint/reply.  
    *deliverability research.*

### 5.10 Поведение / пробелы / Chatix / junior / ИП

53. **Q:** Сколько лет Python?  
    **A:** РИАЦ + Cortex сейчас; 10 лет коммерции в основном Android. Не четыре года Python в банке.

54. **Q:** Kafka / Redis?  
    **A:** В проде не поднимал. В Cortex нет брокера; warmup — in-process/n8n HTTP.

55. **Q:** Kubernetes?  
    **A:** Нет. Compose. На visорах 8 GB K8s не предлагать.

56. **Q:** GitLab CI?  
    **A:** Git + pytest + образы да; автор пайплайна GitLab — нет, пока не сделан C8. «Готов по образцу команды».

57. **Q:** ИП и 2000 ₽/ч?  
    **A:** Как в screening md: формат ок, ставка, 176 ч ориентир, заказчик 8/5 приоритет.

58. **Q:** Совмещение?  
    **A:** Не два фуллтайма. Cortex+отчёты без срыва дедлайна. На проекте их календарь.

59. **Q:** Почему junior Солвиум при 10 годах?  
    **A:** Junior **их** стека (Tortoise, тележки). Не архитектор парка. Менторинг — плюс.

60. **Q:** Chatix нет в резюме?  
    **A:** Платформы нет. Умею править промпт: длина, оффер, один CTA, как validator/guardrail на письме.

61. **Q:** Instantly «интеграция»?  
    **A:** Форма sequence в БД. Живой Instantly = рассылка и риск спама — не делали.

62. **Q:** Тестовое на доске: нарисуй поток письма.  
    **A:** Person → find_email → generate → validate → check_deliverability → decide hold → save_draft.

---

## 6. Питч на 90 секунд (все вакансии)

Outreach AI Cortex — B2B-outreach на FastAPI и PostgreSQL в Docker Compose. Компания парсится, чанки в Chroma, письмо через облачный LLM, агент LangGraph с hold по умолчанию, граф знакомств в Neo4j, поиск email паттернами (Hunter/Apollo только с ключом, SMTP-проверки нет). Репозиторий на GitHub. На работе — Python и SQL по отчётам. Стек вакансии закрываю тем, что есть в коде; пробелы (Tortoise, GitLab CI, Kafka) называю сразу.

---

## 7. Как пользоваться карточками

- Вслух, без файла: 10 карточек утром по дорожке ближайшей вакансии.
- После ответа открыть файл в репо на 2 минуты — не зубрить наизусть строки.
- Перед созвоном: раздел 1 (вакансия) + 5.10 (красные флаги) + питч.

Сжатый трек реализации продукта (не собес): [docs/day-prompts/README.md](../day-prompts/README.md).
