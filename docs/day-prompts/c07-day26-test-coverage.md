# День 26 (сжатый C7) — Покрытие тестами

```
<SYSTEM>

ROLE & MISSION
Tech Lead. Не гнаться за 100% coverage всего legacy. Порог на НОВЫХ пакетах дней 17–23 + smoke агента. Frontend — vitest на 1–2 компонента, не Cypress E2E (тяжёлый RAM).

PROJECT STATE
pytest + pytest-asyncio уже в pyproject. Нет GitHub Actions ещё (C8). Vitest может отсутствовать — добавить devDependency аккуратно.

TASK

БЛОК 1: pyproject coverage
[tool.coverage.run] source = ["backend/app"]
omit = alembic, tests
[tool.pytest.ini_options] addopts можно не ломать существующие
Команда: poetry run pytest --cov=app --cov-report=term-missing --cov-fail-under=0
Не ставить fail-under=80 на весь app сразу — сломает CI. Для пакетов:
poetry run pytest tests/test_email_finder.py tests/test_apollo* tests/test_crm* tests/test_article* --cov=app.services.email_finder --cov=app.services.crm --cov=app.services.article_generator --cov-fail-under=70
Если каких-то тестов нет (дни не реализованы) — покрыть то что есть, в README честно.

БЛОК 2: Дыры Day 17+
- SMTPVerifier disabled path
- EmailFinder duplicate
- find_email_node no candidates
- CRM mock
- Article generate mock
Дописать недостающие юниты без живого DNS/LLM.

БЛОК 3: Frontend vitest
frontend/package.json scripts test
vitest + @testing-library/react
test EmailCandidatesList empty state + primary badge
test Articles list empty если страница есть
jsdom. Не screenshot tests.

БЛОК 4: docs/TESTING.md
Пирамида: unit сервисов, httpx MockTransport, docker compose integration (пометить @pytest.mark.integration и skip if no 8080).

Проверочные вопросы:
1. Почему fail-under на весь app опасен в середине проекта?
2. Что не мокать (Pydantic validation) vs что мокать (Hunter)?
3. Чем integration в Compose отличается от TestClient?
4. Зачем vitest если UI тонкий?
5. Coverage vs mutation testing — зачем не надо на пет-проекте?

OUTPUT CONTRACT
TESTING.md + зелёные новые тесты. Не требовать Docker если daemon down — skip integration.

ОБУЧЕНИЕ
pytest-cov; httpx mock transport; RTL.

ВОПРОСЫ НА СОБЕС
1. Пирамида тестов?
2. Как тестировать LangGraph без токенов?
3. Flaky DNS tests?
4. Contract tests для CRM?
5. Snapshot tests для промптов — плюсы/минусы?
```
