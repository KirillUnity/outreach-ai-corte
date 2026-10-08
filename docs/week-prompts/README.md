# Недельные промпты: портфолио-гайды (4 недели)

Пакет для Cursor **Agent Mode**. Каждый файл — самодостаточный недельный промпт. **Код продукта этими файлами не пишется**, кроме явного аудита в неделе 4 (там можно точечно починить только если OUTPUT CONTRACT разрешает; по умолчанию — markdown-аудит, без рефакторинга).

Копируете **весь** файл недели в **новый** чат в корне `C:\Work\PetAI`. Один чат = одна неделя. Не смешивать с [day-prompts](../day-prompts/README.md).

Выход агента: `docs/guide/` (RU + короткие EN-врезки для собеса). Не копипастить [ARCHITECTURE.md](../ARCHITECTURE.md) / [DEMO.md](../DEMO.md) / [TESTING.md](../TESTING.md) целиком — ссылаться и дополнять.

## Календарь

| # | Файл | Тема | Выход |
|---|------|------|--------|
| 1 | [w01-architecture-runbook.md](w01-architecture-runbook.md) | Схемы, как работает, запуск и проверка | [docs/guide/how-it-works.ru.md](../guide/how-it-works.ru.md) (собрано) |
| 2 | [w02-python-for-kotlin.md](w02-python-for-kotlin.md) | Методы, паттерны, Python vs Kotlin | `docs/guide/python-for-kotlin-devs.ru.md` |
| 3 | [w03-tests-and-ci.md](w03-tests-and-ci.md) | Тесты и CI с примерами | `docs/guide/tests-and-ci.ru.md` |
| 4 | [w04-interview-solid-asyncio.md](w04-interview-solid-asyncio.md) | Собес, SOLID/DRY/KISS, asyncio как корутины | `docs/guide/interview-talk-track.ru.md`, `docs/guide/solid-asyncio-audit.ru.md` |

## Coroutine в этом репо

Kotlin Coroutines **нет**. В промптах «корутина» = **asyncio**: `async def` ≈ `suspend`, не блокировать event loop, `httpx`/`AsyncSession` ≈ IO. Поиск `time.sleep`, sync `requests`, sync SQLAlchemy в `async def`.

## Правила

- Python 3.12, FastAPI, Docker Compose only, 8 GB RAM, облачные LLM / моки
- Не врать Kafka / Kubernetes / 4 года Python-микросервисов
- Не коммитить `.env`; не описывать живой SMTP RCPT как фичу
- Коммит гайдов — только если пользователь просит
