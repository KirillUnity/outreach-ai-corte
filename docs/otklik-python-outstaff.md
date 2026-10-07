# Отклик на вакансию Senior Python (аутстафф)

Скопируйте блок ниже в hh / почту как есть.

---

Здравствуйте!

Кирилл Соколов, 34 года, Новороссийск, работаю удалённо. Откликаюсь на Senior Python: готов к бенчу и гибкой загрузке, переговоры и поиск проектов оставляю вам.

По бэкенду на Python сейчас два контура. На основной работе (ГАУ РО РИАЦ) — Python + SQL/SQLite + REST/JSON: управленческая и годовая отчётность, связанные таблицы, сверки, выгрузки, автозагрузка из БД и API, чтобы ручной ввод не затирал импорт. Параллельно сам спроектировал и веду Outreach AI Cortex — B2B-outreach на FastAPI + async SQLAlchemy + PostgreSQL, RAG (ChromaDB), LangGraph-агент, трассировка Langfuse, граф в Neo4j, React UI, всё в Docker Compose:

https://github.com/KirillUnity/outreach-ai-corte

Там же то, что у вас в плюсах по LLM/RAG: облачные модели (без локального инференса), пайплайн генерации писем с валидацией и guardrails, проверка SPF/DKIM/DMARC, эмулятор прогрева ящиков. OpenAPI из коробки FastAPI, юнит-тесты на сервисы.

Коммерческий стаж около 10 лет, полный цикл: от постановки и архитектуры до релиза, поддержки и оптимизации. Основной прод-трек — Android/Kotlin (Clean Architecture, unit/UI-тесты, JWT, WebSocket, Ktor-клиент). Отдельно — ComePay: финтех, кассовое ПО, устройства, периферия. На комплексе Prognoz (прогнозирование и планирование для ведомств) — Kotlin Ktor-серверы, слои domain/data, SQLite, миграция нескольких продуктов в общий login-shell: та же дисциплина, что routers / services / схемы на FastAPI, плюс brownfield.

Английский B1 — документация и переписка с заказчиком в порядке.

Честно по чеклисту вакансии: коммерческого Python не «четыре года микросервисов с Kafka и Kubernetes». Django в проде не было. Kubernetes не деплоил — Docker Compose да. Kafka и Redis PubSub готов подтянуть на проекте; асинхронный FastAPI, PostgreSQL, интеграции и наблюдаемость через трейсинг — уже в Cortex и на текущей работе. Ищу как раз дополнительный проект, где этот стек станет основным.

Готов созвониться.
+7 904 449-69-21 (WhatsApp, Telegram, Viber)
ksbloger@gmail.com

---

## Как поправить резюме (по желанию)

Сейчас файл называется «Python-разработчик», а хронология почти вся Android — на скрининге это режет. Имеет смысл:

1. Заголовок: «Python / backend (FastAPI) · Android senior, ~10 лет».
2. Сверху 6–8 строк: РИАЦ (Python, SQL, REST) + Cortex (FastAPI, Postgres, Docker, RAG) + ссылка на Git.
3. ComePay явно пометить как финтех.
4. Prognoz — отдельным пунктом «Ktor API, слои, SQLite», не как FastAPI.
5. В навыках: FastAPI, asyncio, SQLAlchemy 2, PostgreSQL, Docker Compose, pytest; Kafka/K8s не ставить как прод-опыт.
6. Django/Flask не добавлять.
7. Английский B1 оставить как есть.
