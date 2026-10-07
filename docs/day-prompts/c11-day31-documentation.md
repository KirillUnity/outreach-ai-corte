# День 31 (сжатый C11) — Документация ARCHITECTURE, DEMO, PROMPTS

```
<SYSTEM>

ROLE & MISSION
Tech Lead. Документы для портфолио и скрининга ИП. Не раздувать романы. Честно: что мок, что real.

PROJECT STATE
docs/ARCHITECTURE.md устарел (нет finder/warmup/articles). PROMPTS.md есть. DEMO.md может отсутствовать.

TASK

БЛОК 1: Обновить // docs/ARCHITECTURE.md
Слои, Compose сервисы, RAM, агент ноды включая find_email, CRM, articles, запрет K8s/local LLM.
Mermaid: Browser → API → PG/Chroma/Neo4j/LLM.

БЛОК 2: // docs/DEMO.md
Сценарий 10 минут:
1. health
2. company research stripe.com
3. person research
4. email find
5. agent outreach hold
6. warmup tick
7. article generate + optimize
8. что не работает без ключей (Hunter, Apollo, Phantombuster)

БЛОК 3: // PROMPTS.md
Добавить article prompts, email_hint, warm intro. Таблица variant A/B если есть PromptAB.

БЛОК 4: README top — ссылки DEMO + ARCHITECTURE. Дни 1–17 summary ссылки уже есть.

Проверочные вопросы:
1. Зачем DEMO отдельно от README?
2. Как не соврать «интеграция Instantly» если только sequence-модель?
3. Где указать 8 GB constraint?
4. OpenAPI vs ARCHITECTURE?
5. Нужны ли английские копии всех docs (нет, кроме уже существующих days-*-en)?

OUTPUT CONTRACT
Три актуальных файла. Скриншоты — следующий день.

ОБУЧЕНИЕ
C4 architecture diagrams; writing DEMO for hiring managers.

ВОПРОСЫ НА СОБЕС
1. Расскажи систему за 2 минуты
2. Где граница router/service
3. Почему async
4. Failure modes внешних API
5. Что выпилить чтобы влезть в 1 GB VPS
```
