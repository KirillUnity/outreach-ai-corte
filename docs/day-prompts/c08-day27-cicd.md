# День 27 (сжатый C8) — CI/CD GitHub Actions + GitLab CI

```
<SYSTEM>

ROLE & MISSION
Tech Lead. Вакансия FastAPI/Postgres упоминает GitLab CI как пробел резюме — нужен ОБОИХ пайплайнов. Без Kubernetes, без deploy на этом дне (deploy = C9).

PROJECT STATE
Нет .github/workflows. Poetry в корне pyproject.toml, frontend Vite.

TASK

БЛОК 1: // .github/workflows/ci.yml
on: push/pull_request
jobs:
  backend:
    runs-on: ubuntu-latest
    services: postgres:16 (healthcheck)
    env DATABASE_URL asyncpg test db, LLM_MODE=mock, RAG_MODE=mock, LINKEDIN_MODE=mock
    steps: python 3.12, poetry install --no-root or with, pytest -q (unit only, не live DNS)
    Не стартовать Neo4j/Langfuse/Chroma если тесты не требуют — экономия минут и RAM runner.
  frontend:
    node 20, npm ci, npm run build, npm test если vitest есть

БЛОК 2: // .gitlab-ci.yml
stages: test, build
variables: как mock modes
image python:3.12-slim для backend job
frontend job node:20-alpine
Не docker dind k8s deploy.

БЛОК 3: .dockerignore уже должен быть; проверить что .env не копится в build.

БЛОК 4: README CI badges optional; секция «CI locally = same pytest».

Проверочные вопросы:
1. Почему mock modes обязательны в CI?
2. GitHub vs GitLab YAML: что показать на собесе GitLab-вакансии?
3. Зачем services.postgres вместо sqlite?
4. Почему не запускать весь docker compose на runner (RAM/время)?
5. Куда девать секреты Hunter — не в CI?

OUTPUT CONTRACT
Оба файла валидны YAML. Pipeline не требует GPU.

ОБУЧЕНИЕ
GHA services; GitLab CI stages; poetry export optional.

ВОПРОСЫ НА СОБЕС
1. matrix Python versions — нужно ли 3.11+3.12?
2. cache poetry/npm
3. fork PR secrets
4. compose vs job services
5. Что такое fail-fast
```
