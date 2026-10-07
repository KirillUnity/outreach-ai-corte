# День 32 (сжатый C12) — Скрины, GIF, сценарий видео (бывшие 32+33)

```
<SYSTEM>

ROLE & MISSION
Агент готовит чеклист и скрипт. Человек записывает видео и делает скрины. Не генерировать бинарные PNG в git без нужды (тяжёлые). Можно docs/demo/README.md с именами файлов.

TASK

БЛОК 1: // docs/demo/SCREENSHOTS.md
Чеклист (галочки):
- /dashboard
- /companies/:domain research + recommended targets
- /persons/:id email candidates PRIMARY
- /graph
- /warmup mailbox card + timeline
- /articles preview
- Swagger /docs
- Langfuse UI если ключи (optional)
- Neo4j browser optional
Формат: 1920×1080, без .env на экране, без секретов.

GIF: email find → list candidates (если умеете screen-to-gif; иначе 3 png).

БЛОК 2: // docs/demo/VIDEO_SCRIPT.md
5 минут, русский:
0:00 проблема холодного outreach
0:30 стек (FastAPI, PG, RAG, LangGraph) + GitHub URL
1:00 демо research company/person
1:40 email finder (паттерны, не обещать Hunter без ключа)
2:10 агент hold + guardrails
2:40 warmup emulator
3:10 статья SEO (КиберСтатьи)
3:40 n8n JSON + CRM mock
4:10 ограничения: моки, 8 GB, нет K8s
4:40 призыв: вопросы по архитектуре
Текст закадра дословно, чтобы читать с листа.

БЛОК 3: Не коммитить 50 MB mov. В .gitignore *.mp4 если нужно.

Проверочные вопросы:
1. Почему не показывать .env?
2. Зачем говорить «мок» вслух на видео?
3. 5 минут vs 15 — почему короче лучше для hh?
4. Нужен ли английский дубль? (опционально later)
5. Как связать видео с вакансией Chatix (тон промптов, 20 сек)?

OUTPUT CONTRACT
Только markdown чеклист+скрипт. Агент не «снимает» видео сам, если нет записи экрана пользователя.

ОБУЧЕНИЕ
Product demo narrative; portfolio GIFs.

ВОПРОСЫ НА СОБЕС
1. Что показывать если Docker не встал у интервьюера?
2. Запасной путь: swagger + pytest output
3. Как не уйти в туториал LangChain
4. Честный слайд ограничений
5. CTA в конце видео
```
