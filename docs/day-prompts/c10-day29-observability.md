# День 29 (сжатый C10) — Observability: Sentry, Prometheus, Langfuse prod

```
<SYSTEM>

ROLE & MISSION
Tech Lead. Вакансии FastAPI/агенты: tracing есть (Langfuse), Prometheus/Grafana как стек — пробел. Закрыть минимально: /metrics + Sentry SDK optional. Не ставить Grafana+Prometheus серверы в Compose на 8 GB (съедят RAM). Метрики — endpoint для внешнего scrape.

PROJECT STATE
Langfuse no-op без ключей. FastAPI health. Нет sentry.

TASK

БЛОК 1: Settings
sentry_dsn: str = ""
sentry_enabled: bool = False
prometheus_enabled: bool = True

БЛОК 2: Sentry
Если dsn пустой — не init.
Иначе sentry_sdk.init FastAPIIntegration, traces_sample_rate=0.1 в prod.
Не слать PII (email тел) в before_send scrub.

БЛОК 3: // backend/app/api/routers/metrics.py
GET /metrics (не обязательно под /api/v1 чтобы совпасть с Prometheus path — допустим /metrics на app root в main.py)
prometheus_client Counter http_requests, Histogram latency, Gauge agent_runs_total optional
Без prometheus_client если не хотите dep — отдать text/plain вручную с счётчиками в memory (проще, меньше dep). Предпочтительно prometheus_client slim.

БЛОК 4: Langfuse prod notes в docs/OBSERVABILITY.md
LANGFUSE_HOST, keys, sample_rate 0.1, отдельный RAM.

БЛОК 5: Тесты /metrics 200; sentry disabled no crash.

Проверочные вопросы:
1. Почему Grafana не в dev compose?
2. Чем Langfuse traces лучше Prometheus для LLM?
3. Зачем scrub email в Sentry?
4. Cardinality labels (не ставить person_id в label)?
5. /metrics публичный — риск?

OUTPUT CONTRACT
Работает без DSN. Документ как подключить scrape на VPS (prometheus.yml job) без запуска Grafana в репо.

ОБУЧЕНИЕ
OpenTelemetry vs Langfuse; RED metrics; Sentry sampling.

ВОПРОСЫ НА СОБЕС
1. Tracing vs metrics vs logs
2. Exemplars
3. PII в LLM traces
4. SLO для /agent/outreach (latency + cost)
5. Почему не логировать полный промпт в Grafana
```
