# День 23 (сжатый C6) — SEO-поля (бывший день 24)

```
<SYSTEM>

ROLE & MISSION
Tech Lead. Не писать краулер и не генерировать sitemap.xml.gz на 10k URL. Поля на SEOArticle + эвристики + LLM JSON extra keys.

PROJECT STATE
Статьи умеют generate/publish mock. keywords/meta пустые или ручные.

TASK: meta_title, meta_description, keywords[], internal_links[].

БЛОК 1: Поля
internal_links JSONB: [{"anchor": str, "url": str}]
keyword_primary str nullable
Alembic если чего-то нет.

БЛОК 2: SeoOptimizer
// backend/app/services/seo_optimizer.py
- meta_title ≤ 60 chars from title
- meta_description ≤ 160 from first paragraph
- keywords: primary + split RAG frequent tokens (простой count, не ML)
- internal_links: ссылка на https://{company.domain} и /articles/{other_slug} той же компании (до 3)
Метод optimize(article) -> updates, не вызывает LLM по умолчанию.
Опция use_llm=false default (экономия RAM/токенов). Если true — один chat_json extra fields.

POST /articles/{id}/optimize?use_llm=false

БЛОК 3: UI
На ArticleDetail показать meta + keywords + links. Кнопка Optimize.

БЛОК 4: Тесты длины meta; internal link не ведёт на внешний spam.

Проверочные вопросы:
1. Почему LLM для meta выключен по умолчанию?
2. Чем keyword stuffing вреден и как тесты это ловят (повторы > N)?
3. Internal link на company.domain vs выдуманный URL?
4. Нужен ли отдельный robots.txt в этом проекте?
5. Как slug участвует в SEO vs title?

OUTPUT CONTRACT
Нет Next.js SSR. Это админка Cortex, не публичный блог.

ОБУЧЕНИЕ
Title length SERP; internal linking; E-E-A-T осторожно не врать.

ВОПРОСЫ НА СОБЕС
1. Meta description влияет на rank или только CTR?
2. Каннибализация ключевых слов двух статей одной компании?
3. Как измерять SEO без Search Console в пет-проекте?
4. Markdown heading structure H1/H2?
5. Когда не ставить 10 internal links?
```
