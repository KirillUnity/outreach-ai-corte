# День 22 (сжатый C5) — Автопостинг + минимальный UI (бывшие 22+23)

```
<SYSTEM>

ROLE & MISSION
Tech Lead. Публикация — МОК (лог + timestamp), не WordPress/Telegram live. UI простой: список, форма generate, preview markdown. Без full calendar widget.

PROJECT STATE
SEOArticle после C4. n8n article_publish.json заготовка с дня C2.

TASK: schedule, mock publisher, n8n webhook, React pages.

БЛОК 1: Поля статьи
scheduled_at timestamptz nullable, published_at, publish_channel Literal mock|webhook (string col), publish_url nullable
Миграция.

БЛОК 2: ArticlePublisher
// backend/app/services/article_publisher.py
async def publish(article_id) -> article
- если channel mock: status=published, published_at=now, publish_url="https://example.invalid/posts/{slug}"
- если webhook: POST settings.content.publish_webhook_url JSON {title,slug,body} ; 2xx → published else failed
Никакого FTP/SSH.

POST /articles/{id}/schedule {scheduled_at}
POST /articles/{id}/publish  (сразу)
POST /articles/tick-due  — все scheduled_at <= now and status=scheduled (X-Admin-Token как warmup tick-all)

БЛОК 3: n8n
Обновить n8n/workflows/article_publish.json: Cron hourly → POST /articles/tick-due + token.

БЛОК 4: Frontend
types.ts SEOArticle
api/articles.ts
pages/ArticlesPage.tsx — список, кнопка Generate (domain + keyword)
pages/ArticleDetailPage.tsx — preview (простой pre/markdown text), Schedule datetime-local, Publish
App.tsx routes /articles /articles/:id
Layout nav «Articles»
Не ставить тяжёлые markdown-WYSIWYG.

БЛОК 5: Тесты publisher mock; tick-due не трогает future.

Проверочные вопросы:
1. Почему tick-due админский, а не публичный?
2. Чем mock publish_url с .invalid полезен в демо?
3. Почему нет календаря как в Google Calendar?
4. Как n8n и in-process scheduler не двойной publish? (unique status transition scheduled→published)
5. Что если webhook 500 — retry?

OUTPUT CONTRACT
Идемпотентный publish: повтор published → 200 no-op.
Проверка UI: если нет browser tools — сказать что не проверено в браузере.

ОБУЧЕНИЕ
Content calendar vs queue; webhook CMS; idempotency keys.

ВОПРОСЫ НА СОБЕС
1. Outbox pattern для публикаций?
2. Как не опубликовать черновик с галлюцинацией?
3. SLA n8n vs FastAPI BackgroundTasks?
4. Preview vs stored markdown?
5. GDPR: статья про компанию vs персональные данные лида?
```
