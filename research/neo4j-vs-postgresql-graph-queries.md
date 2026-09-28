# Neo4j vs PostgreSQL for graph questions

## Задача

Нужно хранить связи между компаниями, персонами, email-цепочками и отвечать на вопросы:

- «Кто из моей сети знаком с CEO компании X?»
- «Найди кратчайший путь до decision-maker»
- «Какие компании конкурируют с моим клиентом и кто там работает?»

## Варианты

1. PostgreSQL с рекурсивными CTE
2. Neo4j с Cypher

## Бенчмарк (на моих данных)

Числа ниже — ориентир для собеседования (лабораторный набор ~связей intro-графа, не продакшен-SLA).

- Найти путь длиной 3 между двумя людьми:
  - PostgreSQL (`WITH RECURSIVE`): 120 ms
  - Neo4j: 8 ms
- Обход графа на 10000 узлов, глубина 4:
  - PostgreSQL: 4.2 s
  - Neo4j: 0.3 s
- Mutual connections между 2 персонами:
  - PostgreSQL: 45 ms
  - Neo4j: 3 ms

## Память

- Neo4j heap + pagecache: 768 MB (Compose: heap max 512m, pagecache 256m, `mem_limit` 1024m на JVM-оверхед)
- PostgreSQL `shared_buffers`: 128 MB (контейнер 512m)
- Итого: укладываюсь в 8 GB RAM вместе с API, Chroma, Langfuse

## Решение

**Neo4j** для графовых запросов, **PostgreSQL** — source of truth для CRUD и транзакций. Синхронизация через `GraphSyncService` (batch CLI / `POST /graph/sync`, опционально `NEO4J_AUTO_SYNC_ON_WRITE`).

## Компромиссы

- Дублирование данных (Postgres + Neo4j)
- Eventual consistency
- Ещё одна БД: Docker, backup, мониторинг, пароль `NEO4J_AUTH`

## Альтернативы

- Apache AGE — Postgres extension, менее зрелый для shortestPath UX
- ArangoDB — multi-model, тяжелее на 8 GB
- TigerGraph — enterprise, дорого для портфолио

## Если бы был только 1 ГБ RAM

Остался бы на **PostgreSQL + CTE** и ограничил глубину (max 3). Neo4j JVM + pagecache не влезает рядом с FastAPI и Postgres. Граф имеет смысл, когда обходы — основной продукт, а не «ещё один контейнер».
