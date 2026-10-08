# Сжатый трек: 14 техпромптов (дни 18–35)

Пакет для Cursor **Agent Mode**. Каждый файл — самодостаточный дневной промпт в формате Дня 17: ROLE, PROJECT STATE, блоки, команда проверки, проверочный вопрос, OUTPUT CONTRACT, вопросы на собес.

Код продукта этими файлами **не пишется** — копируете файл в новый чат и реализуете день там.

## Что уже в git (не повторять)

Дни **1–17** закрыты в `cursor/day1-bootstrap-fastapi-stack` (Email Finder — коммит Day 17). Есть: FastAPI, Postgres, Alembic, RAG, LangGraph (~12 нод с `find_email`), Langfuse, Neo4j, React UI, deliverability DNS, warmup emulator, Hunter/pattern finder, LinkedIn mock + каркас Phantombuster, n8n warmup tick.

## Карта вакансий → дни трека

| Вакансия | Какие промпты закрывают пробел | Чего нет в треке (намеренно) |
|----------|--------------------------------|------------------------------|
| FastAPI / PostgreSQL | c07 тесты, c08 CI (GitHub **и GitLab**), c09 Compose prod, c10 `/metrics` | Kubernetes, Kafka |
| FastAPI / агенты | c01 внешние API, c11 PROMPTS/ARCHITECTURE, c13 собес | Redis/брокер как обязательный прод |
| Python аутстафф | весь трек + честный стек в c13/c14 | Локальные LLM, K8s |
| Chatix (боты в продажах) | c11 промпты/тон, c13 блок Chatix | Отдельный продукт Chatix |
| Скрининг ИП 2000 ₽/ч | c11 DEMO, c14 Git-ссылка и метрики | Выдуманные 4 года Python / Kafka |
| МетаПромт / КиберСтатьи | c01 Apollo/Phantombuster/Instantly-shape, c02 CRM+n8n, c04–c06 статьи | Живой SMTP, скрейп LinkedIn, спам-рассылки |

## Календарь (14 рабочих дней)

| # | Файл | Было в 35-дневке | Тема |
|---|------|------------------|------|
| 1 | [c01-day18-enrichment-providers.md](c01-day18-enrichment-providers.md) | 18 | Apollo + Phantombuster search + Instantly Sequence (без SMTP) |
| 2 | [c02-day19-crm-n8n.md](c02-day19-crm-n8n.md) | 19 | Bitrix24/retailCRM мок + n8n outreach/articles |
| 3 | [c03-day20-research-notes.md](c03-day20-research-notes.md) | 20 | Только research md (deliverability + агенты B2B) |
| 4 | [c04-day21-seo-article-factory.md](c04-day21-seo-article-factory.md) | 21 | SEOArticle + генератор RAG/LLM |
| 5 | [c05-day22-autopost-ui.md](c05-day22-autopost-ui.md) | 22+23 | Расписание, mock publish, простой UI |
| 6 | [c06-day23-seo-fields.md](c06-day23-seo-fields.md) | 24 | Meta, keywords, internal links |
| 7 | [c07-day26-test-coverage.md](c07-day26-test-coverage.md) | 26 | pytest-cov + vitest |
| 8 | [c08-day27-cicd.md](c08-day27-cicd.md) | 27 | GitHub Actions + `.gitlab-ci.yml` |
| 9 | [c09-day28-vps-compose.md](c09-day28-vps-compose.md) | 28 | `docker-compose.prod.yml` + DEPLOY.md |
| 10 | [c10-day29-observability.md](c10-day29-observability.md) | 29 | Sentry, Prometheus `/metrics`, Langfuse prod |
| 11 | [c11-day31-documentation.md](c11-day31-documentation.md) | 31 | ARCHITECTURE, DEMO, PROMPTS |
| 12 | [c12-day32-demo-assets.md](c12-day32-demo-assets.md) | 32+33 | Скрины/GIF + сценарий 5-мин видео |
| 13 | [c13-day34-interview.md](c13-day34-interview.md) | 34 | Ответы под ваши отклики |
| 14 | [c14-day35-ship.md](c14-day35-ship.md) | 35 | Пуш, пост, метрики репо |
| — | [c15-day25-content-marketing.md](c15-day25-content-marketing.md) | **25 restored** | Content-marketing essay (markdown only) |
| — | [c16-day30-locust.md](c16-day30-locust.md) | **30 restored** | Locust read-only, RAM-safe (not in Compose) |

**Days 25 and 30** were skipped in the original 14-prompt pack and are **no longer unimplemented**. Capture notes for day 33 live in `docs/demo/CAPTURE.md` (c12 still owns the checklist + script).

## Правила для всех дней

- Python 3.12, FastAPI, async SQLAlchemy, Poetry, Docker Compose **only**
- 8 GB RAM / Iris Xe 128 MB VRAM — **никаких** Ollama/PyTorch
- Облачные LLM; `LLM_MODE=mock` / `RAG_MODE=mock` в CI
- Не коммитить `.env`; не делать живой SMTP `RCPT TO`; не скрейпить LinkedIn
- Коммит и push — только если промпт дня явно просит
- После каждого блока — проверочный вопрос (для самопроверки, не для пользователя в чате реализации)

## Как запускать день

1. Открыть новый Agent-чат в корне `C:\Work\PetAI`.
2. Вставить **весь** файл дня.
3. Не смешивать два дня в одном чате.
4. Если Docker Desktop выключен — агент пишет код и тесты, прогон в Compose откладывается, но миграции в `alembic/versions/` всё равно создаются файлами.
