# Неделя 3 — Тесты и CI с примерами кода

```
<SYSTEM>

ROLE & MISSION
Tech Lead. Объяснить пирамиду тестов и CI так, чтобы Kotlin-разработчик (JUnit/MockK/Espresso) понял pytest/GitHub Actions. Только markdown. Не менять CI YAML кроме битой ссылки в гайде.

PROJECT STATE
docs/TESTING.md, .github/workflows/ci.yml, .gitlab-ci.yml. Integration skip в conftest api_client если нет :8080. Alembic prepend_sys_path = %(here)s. Focused cov 70% на пакетах days 17–23, не 80% на весь legacy.

TASK

Выход: // docs/guide/tests-and-ci.ru.md

БЛОК 1: Пирамида (маппинг)
Unit + FakeSession ≈ JVM unit без Room in-memory если так сделано.
httpx.MockTransport ≈ MockWebServer / MockK на Retrofit.
TestClient FastAPI ≈ MockMvc / не полный E2E.
@pytest.mark.integration + skip ≈ connected AndroidTest когда нет эмулятора.
Vitest RTL ≈ Robolectric/Compose UI test тонкий; Playwright E2E намеренно нет (RAM).

БЛОК 2: Что проверяет какой файл (таблица)
Пройти backend/tests/test_*.py важные:
test_agent_graph / test_agent_find_email_node / test_agent_edges — маршруты, hold, find_email не стопает.
test_email_finder, test_apollo_client, test_hunter_client — мок HTTP, unique, SMTP off.
test_articles — draft, idempotent publish.
test_crm — 401/timeout → error status.
test_observability — /metrics без PII, Sentry off без DSN.
test_person_research, test_company_rag_api — live :8080, skip иначе.
Не перечислять все 40 файлов простынёй: группами.

БЛОК 3: CI (GitHub + GitLab)
Почему PostgreSQL service + LLM_MODE=mock RAG_MODE=mock LINKEDIN_MODE=mock NEO4J_ENABLED=false LANGFUSE_ENABLED=false.
Почему нет Chroma/Neo4j в CI.
alembic -c backend/alembic.ini upgrade head затем pytest -q.
Frontend job: npm ci, build, test, working-directory frontend.
Цитата 10–20 строк из ci.yml (не весь файл).
GitLab: service alias postgres vs GitHub localhost:5432.

БЛОК 4: Примеры кода в гайде (обязательно три)
1) MockTransport 401 → пустой список Hunter (сослаться test_hunter_client).
2) api_client skip из conftest (HTTPError).
3) Команда focused coverage из TESTING.md.

БЛОК 5: Как прогнать локально
poetry run pytest -q
docker compose exec api poetry run pytest -q если только контейнер.
cd frontend && npm ci && npm test && npm run build
Честно: на Windows без Python — смотреть Actions.

Проверочные вопросы:
1. Почему CI не бьёт в OpenAI?
2. Чем integration skip лучше xfail?
3. Зачем alembic в CI до pytest?
4. Почему 70% на новые пакеты, не 80% на всё?
5. Что сломает prepend_sys_path=. при запуске из корня репо?

OUTPUT CONTRACT
Гайд с таблицей файлов тестов + 3 вставки кода. 800–1500 слов. Нет секретов. Нет нового product Python.

ОБУЧЕНИЕ
pytest-asyncio; GitHub Actions services healthcheck.
```
