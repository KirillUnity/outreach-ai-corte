# День 20 (сжатый C3) — Deep Research notes (без кода продукта)

```
<SYSTEM>

ROLE & MISSION
Tech Lead. Этот день — только markdown в research/. Не менять Python/React, кроме ссылок в README если нужно.

PROJECT STATE
Deliverability DNS (SPF/DKIM/DMARC/MX) и LangGraph агент уже в коде. Нужны шпаргалки для собеса FastAPI/агенты и МетаПромт.

TASK: Два файла + оглавление в README.

БЛОК 1: // research/b2b-email-deliverability.md
Структура:
- Inbox vs spam: репутация домена, PTR, SPF/DKIM/DMARC alignment
- Почему свой RCPT TO — плохая идея (уже в email-finding-strategies.md — не копипастить, сослаться)
- Warmup кривая vs Instantly/Mailreach как продукты (концепт, без интеграции)
- Метрики: bounce, complaint, open (как proxy, и почему open умирает с Apple MPP)
- Как Cortex это моделирует: DomainHealth snapshot vs live DNS checker, WarmupEmulator
Объём 800–1500 слов, не простыня.

Проверочный вопрос: Почему open rate плохая KPI в 2024+?

БЛОК 2: // research/ai-agents-in-b2b-outreach.md
- LangGraph vs линейный chain (у нас StateGraph, human_approval)
- Риски: галлюцинации в письме, PII, автоотправка
- Guardrails vs validator vs LLM-as-judge
- Стоимость токенов и Langfuse
- Когда агент не нужен (один generate-email endpoint)
Сослаться на существующие research/langgraph-vs-langchain-agents.md, langfuse-*.md — не дублировать, синтез.

Проверочный вопрос: Зачем require_human_approval=true в dev?

БЛОК 3: README Docs — две ссылки.

БЛОК 4: Коммит если просят:
git commit -m "[RESEARCH] Day 20: B2B deliverability and outreach agents notes"

OUTPUT CONTRACT
Нет миграций, нет нового Python. Качество: можно читать вслух на собесе 3 минуты на файл.

ОБУЧЕНИЕ
Google MPP; RFC 7208 SPF; LangGraph docs concepts.

ВОПРОСЫ НА СОБЕС
1. DMARC quarantine vs reject?
2. Catch-all и bounce?
3. Чем агент отличается от cron + LLM?
4. Как оценить cost per draft?
5. Когда не использовать агента?
```
