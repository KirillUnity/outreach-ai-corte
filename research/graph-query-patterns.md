# Паттерны Cypher для B2B-аутрича

## 1. Поиск кратчайшего пути

Когда использовать: warm intro, поиск общего знакомого.

Запрос: `shortestPath((a)-[:CONNECTED_TO*1..6]-(b))`.

В Neo4j hop-count **нельзя** параметризовать (`*..$max_depth` невалиден). В Cortex hops зафиксированы как `*1..6`.

## 2. Mutual connections

Когда использовать: «у нас 3 общих знакомых».

```
(a)-[:CONNECTED_TO]->(m)<-[:CONNECTED_TO]-(b)
```

Направленность должна совпадать с тем, как вы пишете `MERGE` (в Cortex связи двусторонние).

## 3. Influence score

Формула: `direct_connections + 0.5 * second_degree_connections`.

Почему 0.5: второй уровень слабее, но всё ещё сигнал «человек встроен в сеть».

На железе 8 ГБ **не** считаем PageRank через GDS.

## 4. Competitor landscape

`COMPETITOR_OF` пишется в обе стороны: запрос «конкуренты X» не зависит от того, кто кого добавил первым.

## 5. Recommendations

Комбинация: shortest path + influence + отсутствие `PARTICIPATES_IN` EmailThread.

## Оптимизация запросов

- `LIMIT` обязателен везде в HTTP-слое.
- Индексы на `id`, `domain`, `linkedin_url` (см. `init_schema`).
- `EXPLAIN` — план без выполнения; `PROFILE` — с реальными db-hits.

## Антипаттерны

- `MATCH (n)` без `WHERE` / без якоря по indexed property — full scan.
- Variable-length без верхней границы depth.
- Возврат `n` целиком, если нужны 3 поля.
- GDS WCC / PageRank на Iris Xe / 512m heap — не ставим плагин.

Константы: `backend/app/services/graph/queries.py`. Cookbook: `docs/graph-recipes.md`.
