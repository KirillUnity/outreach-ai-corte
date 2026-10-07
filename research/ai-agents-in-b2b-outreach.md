# AI-агенты в B2B outreach (шпаргалка на собес)

Не дублировать: [langgraph-vs-langchain-agents.md](langgraph-vs-langchain-agents.md), [langfuse-observability-for-llm.md](langfuse-observability-for-llm.md), [llm-prompt-engineering-for-outreach.md](llm-prompt-engineering-for-outreach.md), [PROMPTS.md](../PROMPTS.md).

**Самопроверка:** зачем `require_human_approval=true` в dev? → Даже «идеальный» драфт уходит в **hold**. Нет автоотправки с ноутбука 8 GB / чужого IP. `save_and_send` — stub `mark_sent`.

---

## Русский

### Graph vs линейный chain

Холодное письмо — **не** свободный ReAct: порядок шагов известен. `StateGraph` кодирует политику в коде (load → research? → RAG → enrich_with_graph → **find_email** → generate → validate → deliverability → decide → save). LLM пишет текст, не решает «пропустить ли DMARC». `AgentExecutor` имеет смысл, когда модель сама выбирает инструменты; здесь это вредно.

Условные рёбра: нет персоны → END; грязный драфт и `iteration < 2` → снова generate; `decide` → hold/reject/send. `validation_errors` **overwrite**, не `add`: иначе реген не снимет старый spam. `thread_id = person_id:uuid4()`, не голый `person_id`.

### Риски

| Риск | Что делаем |
|------|------------|
| Галлюцинации фактов о компании | RAG + «не выдумывай»; hallucination rail |
| PII в письме | guardrail PII, не тащить чужие телефоны |
| Автоотправка | `human_approval`, SMTP stub |
| Стоимость токенов | mock LLM в CI, Langfuse, cost в `agent_runs` |
| Внешние API | Hunter/Apollo/Phantombuster — ключ опционален, fallback mock |

### Guardrails vs validator vs LLM-as-judge

- **OutputValidator** — дешёвые правила: длина, CAPS, spam-слова, JSON поля.
- **GuardrailPipeline** — политика (PII, abuse, structure, «сущности не из RAG»).
- **LLM-as-judge** — дороже и сам галлюцинирует; в Cortex эвристический QualityScorer + трейсы, не второй GPT на каждый черновик в деве.

Слоями: сначала regex, потом rails, человек на hold. Judge — если появится бюджет и офлайн-оценка промптов.

### Стоимость и Langfuse

Счётчик токенов на `chat_json`, `estimated_cost_usd` в драфте и `agent_runs`. Langfuse: generation (промпт/ответ/токены) + spans нод. Пустые ключи → no-op, API жив. Sample rate крутить вниз в prod (промпт дня 29). KPI: **cost per run**, mix hold/send/reject, personalization_score — не «миллион токенов».

### Когда агент не нужен

Один `POST /persons/{id}/generate-email` — если нет research/DNS/graph. Агент оправдан, когда шаги **ветвятся** и нужен аудит `final_state`. Cron + LLM без графа — если всегда один промпт и нет decide. n8n вызывает тот же HTTP, не заменяет StateGraph.

CRM (день 19) и sequence tick **не** крутят агент сами по себе: иначе цикл webhook → outreach → CRM.

---

## English

Outreach is a **fixed policy**, so a LangGraph `StateGraph` beats AgentExecutor: the model writes copy; Python decides routing. Default **hold** (`require_human_approval`). `find_email` does not abort generate. Overwrite reducers on validation. Unique `thread_id` per run.

Risks: hallucinations (RAG + rails), PII, accidental send (no live SMTP), token cost (mock in CI, Langfuse). Validator = cheap rules; guardrails = policy; LLM-as-judge is optional and expensive.

Skip the agent when a single generate-email is enough. Use the graph when you need research, DNS, email discovery, and an auditable decision.
