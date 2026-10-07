# День 21 (сжатый C4) — Контент-фабрика SEOArticle (КиберСтатьи)

```
<SYSTEM>

ROLE & MISSION
Tech Lead. Генерация статей — облачный LLM + RAG по Company.raw_site_text. Никаких локальных моделей.

PROJECT STATE
LLMClient, RAGService, EmailGenerator, OutputValidator, GuardrailPipeline — переиспользовать, не копипастить промпты в сервис.

TASK: Модель статьи, генератор, CRUD, generate endpoint.

БЛОК 1: Модель
// backend/app/models/seo_article.py
SEOArticle:
- company_id FK nullable
- title, slug unique, body_markdown
- language default "ru"
- status: draft|ready|scheduled|published|failed
- keywords JSONB list[str] (пока пусто, заполнит день C6)
- meta_title, meta_description nullable
- rag_context_used JSONB
- tokens_input/output, estimated_cost_usd
- generation_prompt_version str
Timestamp + UUID mixins.

Alembic revision.

БЛОК 2: Схемы Pydantic v2
ArticleCreate, ArticleGenerateRequest (company_domain, keyword, language, max_words=800), ArticleResponse

БЛОК 3: Промпты
// backend/app/services/prompts/article_prompts.py
SYSTEM + USER с {company_name} {rag_context} {keyword} {language} {max_words}
JSON out: title, slug, body_markdown
Запрет выдумывать факты вне RAG (как в email).

БЛОК 4: ArticleGenerator
// backend/app/services/article_generator.py
retrieve RAG → prompt → llm.chat_json → validate (длина, нет spam URL shorteners) → persist SEOArticle status=draft
Reuse LLMClient, RAGService, CostTracker, TracingService.

БЛОК 5: Роутер prefix /articles
POST /generate
GET / {limit,offset,company_id,status}
GET /{id}
PATCH /{id}  (ручная правка title/body)
DELETE /{id}

main.py include_router.

БЛОК 6: Тесты mock LLM
test_generate_persists_article, test_slug_unique_conflict, test_no_rag_still_draft_with_disclaimer

Проверочные вопросы:
1. Почему статья привязана к Company, а не к Person?
2. Зачем JSON от LLM, а не сырой markdown?
3. Как не сжечь токены на 800 слов в CI?
4. Чем ArticleGenerator отличается от EmailGenerator (общая база)?
5. Почему status=draft после generate, не published?

OUTPUT CONTRACT
Нет автопостинга (это C5). Нет UI (C5).

ОБУЧЕНИЕ
RAG for long-form; slug uniqueness; content vs outreach prompts.

ВОПРОСЫ НА СОБЕС
1. Как бороться с галлюцинациями в SEO-тексте?
2. Chunk size для статей vs писем?
3. Кто утверждает публикацию?
4. Мультиязычность?
5. Как версионировать промпт статьи?
```
