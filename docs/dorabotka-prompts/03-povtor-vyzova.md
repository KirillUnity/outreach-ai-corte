# Промпт 3 — повтор внешнего вызова

Вставь этот файл целиком в новый Agent-чат в корне `C:\Work\PetAI`. Пункты 1 и 2 ТЗ в этом чате не делать.

```
ROLE
Ты дорабатываешь Outreach AI Cortex (этот репозиторий). Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, Poetry. 8 ГБ RAM. Исходящий HTTP — httpx async. Живой Hunter, Apollo, SMTP и любые вендорские хосты из тестов не вызывать. Локальных моделей, брокера и Kubernetes не добавлять.

ИСТОЧНИК
Пункт «Повтор внешнего вызова» в C:\Work\CareerAgent\docs\cortex-dorabotka-tz.md.
Приём подмены транспорта уже есть в backend/tests/test_hunter_client.py (httpx.MockTransport). Для новой проверки ответ 429 задаётся так же. Пример из Career Agent (fetch_hh_vacancies) не копировать: вакансий hh.ru в Cortex нет.

УЖЕ ЕСТЬ
- HunterClient._get при 429 пишет warning и find_email возвращает [] (backend/tests/test_hunter_client.py::test_handles_429_rate_limit). Кандидата почты из 429 по-прежнему нет
- 429 сейчас неотличим для вызывающего от «писем нет»: строка попытки нигде не сохраняется
- EmailFinder в backend/app/services/email_finder/finder.py вызывает hunter.find_email и имеет AsyncSession-уровень выше по стеку
- RetryPolicy в backend/app/services/retry_policy.py считает задержку в процессе и в Postgres её не кладёт. Таблицу попыток не подменять этой политикой
- Голова Alembic могла разъехаться. Перед миграцией выполни poetry run alembic heads из backend (или docker compose exec api …, если так принято в репо). down_revision — текущая единственная голова. Вторую голову не создавай
- Модели регистрируются импортом в backend/app/models/__init__.py

СДЕЛАТЬ

1. Таблица outbound_attempts и модель.
   Поля: target (какой внешний вызов, уникальный), attempt_count, last_error, next_attempt_at (timezone-aware), status: failed | succeeded.
   Миграция backend/alembic/versions/<rev>_outbound_attempts.py с upgrade и downgrade.
   Сервис backend/app/services/outbound_attempts.py, AsyncSession, функции:
   - record_failure(target, status_code, error, now) -> Attempt
     Увеличивает attempt_count той же строки target, пишет last_error (для отказа по частоте в тексте есть 429), ставит next_attempt_at строго позже now, status=failed.
     Повторный отказ по тому же target обновляет эту строку. Новую «успешную» строку не создаёт.
   - record_success(target, now) -> Attempt
     status=succeeded только после реального успеха.
     Если перед этим были отказы, attempt_count и last_error остаются читаемыми: история не стирается так, будто отказа не было.
     Успех с первой попытки: attempt_count = 1, last_error пустой, status=succeeded. Вид предшествующих ошибок не создавать.
   now передаётся снаружи, чтобы тест не спал и не зависел от часов.

2. Живой путь Hunter, без сети в тесте.
   HunterClient по-прежнему не ходит в SQL и при 429 не возвращает email.
   Вызывающий код (finder или тонкая обёртка рядом с ним) обязан отличить 429 от пустого успеха. Тихий return [] без записи попытки для включённого Hunter недостаточен.
   target стабильный для того же вызова, например hunter:email-finder:{domain}:{first}:{last}.
   Повторный 429 по тому же target обновляет ту же запись. Уже сохранённые agent_runs, черновики и кандидаты этот код не удаляет и не помечает отправленными.
   Шаг для пользователя выглядит неуспешным: status=failed, пока не было реального успеха.

3. Список, который можно открыть.
   Тонкий роутер GET /api/v1/outbound-attempts (префикс /api/v1, бизнес-логика в сервисе).
   В строке видны attempt_count, last_error, next_attempt_at, status, target.
   Отдельной кнопки отправки письма нет.

4. Тест backend/tests/test_outbound_attempts.py
   - транспорт MockTransport возвращает httpx.Response(429, text="too many requests"); адрес api.hunter.io не запрашивается (assert на request.url хост не нужен снаружи — MockTransport не выпускает сокет; в тесте не использовать сеть)
   - после отказа status=failed, attempt_count > 0, last_error содержит 429, next_attempt_at > now
   - второй отказ того же target увеличивает счётчик и не создаёт вторую строку
   - успех с первой попытки: status=succeeded, attempt_count=1, last_error пустой
   - успех после отказа: status=succeeded, last_error и счётчик всё ещё читаются
   Существующий test_handles_429_rate_limit остаётся зелёным: email по-прежнему не находится.

НЕ ДЕЛАТЬ
Живой HTTP к Hunter, очередь Celery/Redis/Kafka, ретраи во сне внутри теста, SMTP, правка agent graph, коммит без просьбы пользователя.

ПРОВЕРКА
poetry run pytest backend/tests/test_outbound_attempts.py backend/tests/test_hunter_client.py -q

OUTPUT
Миграция, сервис, список попыток, тесты. Одной фразой: 429 пишется в Postgres и повтор идёт в ту же строку.
```
