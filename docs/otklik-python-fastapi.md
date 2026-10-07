# Отклик: Python-разработчик (FastAPI / PostgreSQL)

Скопируйте блок ниже в hh / почту как есть.

---

Здравствуйте!

Кирилл Соколов, 34 года, Новороссийск, удалёнка. Высшее техническое (ТТИ ЮФУ, электроника и приборостроение) и магистратура ЮФУ. Английский B1: документация и деловая переписка. Git — ежедневная практика.

По вакансии закрываю ядро стека на живом коде, не «по учебнику».

Сам спроектировал и веду Outreach AI Cortex — сервис на Python 3.12, FastAPI + Pydantic v2, asyncio (async SQLAlchemy, httpx), типизация, OpenAPI из коробки, PostgreSQL + Alembic, pytest, зависимости через Poetry, Docker Compose:

https://github.com/KirillUnity/outreach-ai-corte

Там же REST-контракты, слои router → service → ORM, RAG/LangGraph, сквозная трассировка LLM и агента в Langfuse. На основной работе (ГАУ РО РИАЦ) — Python + SQL/SQLite + REST/JSON: отчётные контуры, сверки, выгрузки, автозагрузка из БД и API.

Около 10 лет коммерции, полный цикл и работа в команде (Jira, code review, связка с backend/QA). Android/Kotlin в проде: тесты, JWT, WebSocket, Ktor. ComePay — финтех. Prognoz — Ktor-серверы и слои domain/data (не Python, но та же дисциплина API). Наставничество: онбординг и разбор архитектуры по Prognoz (учебный маршрут, ревью границ модулей). Scrum/Kanban — в продуктовых Android-командах.

Честно по плюсам и формулировке «от 4 лет Python-разработчиком»: коммерческий Python сейчас — РИАЦ + Cortex, это не четыре года только на Python в микросервисах. Django/DRF в проде не было — FastAPI да. Kubernetes и Kafka/RabbitMQ — плюс, в проде не поднимал; Docker Compose — да. GitLab CI отдельно не настраивал: Git + pytest + сборка образов; пайплайн CI готов вести по образцу команды.

Ориентир — результат и рост в backend на FastAPI/PostgreSQL. Готов созвониться.

+7 904 449-69-21 (WhatsApp, Telegram, Viber)
ksbloger@gmail.com

---

## Соответствие чеклисту (для себя, в письмо не копировать)

| Требование | Как отвечать на собесе |
|------------|-------------------------|
| Высшее ИТ/техн. | ТТИ ЮФУ электроника + маг. ЮФУ |
| 4 года Python | Не врать: РИАЦ + Cortex; 10 лет коммерции в целом |
| Git | да |
| Python 3.11+, asyncio, typing | 3.12, async FastAPI/SQLAlchemy, type hints |
| FastAPI/Pydantic | да; Django — нет |
| REST, OpenAPI | FastAPI swagger |
| PostgreSQL, Alembic, SQLAlchemy | Cortex |
| pytest | Cortex; пирамида — unit сервисов, интеграционные без живого DNS (моки) |
| poetry | да |
| Docker Compose | да; K8s — нет |
| Kafka/Rabbit | нет, плюс |
| tracing / мониторинг | Langfuse; Prometheus/Grafana как прод-стек — нет |
| GitLab CI | нет как автор пайплайна |
| Scrum/Kanban | Jira/команда Android |
| наставничество | Prognoz onboarding / ревью |
| English B1 | да |
