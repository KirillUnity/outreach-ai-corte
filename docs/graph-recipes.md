# Graph recipes (Cypher cookbook)

Все hop-паттерны с переменной длиной в этом проекте — `*1..6`. Параметр `$max_depth` в Cypher так не подставляется.

## 1. Сотрудники компании

```cypher
MATCH (c:Company {domain: $domain})<-[:WORKS_AT]-(p:Person)
RETURN p LIMIT $limit
```

## 2. Кратчайший путь между людьми

```cypher
MATCH (a:Person {id: $from_id}), (b:Person {id: $to_id})
MATCH path = shortestPath((a)-[:CONNECTED_TO*1..6]-(b))
RETURN path, length(path) AS distance
```

## 3. Общие знакомые двух людей

```cypher
MATCH (a:Person {id: $person_a_id})-[:CONNECTED_TO]->(m:Person)<-[:CONNECTED_TO]-(b:Person {id: $person_b_id})
RETURN DISTINCT m LIMIT $limit
```

## 4. Путь до любого сотрудника целевого аккаунта

```cypher
MATCH (a:Person {id: $person_id}), (c:Company {domain: $domain})<-[:WORKS_AT]-(target:Person)
MATCH path = shortestPath((a)-[:CONNECTED_TO*1..6]-(target))
RETURN path, target, length(path) AS distance
ORDER BY distance ASC LIMIT 1
```

## 5. Influence (1-hop + 2-hop)

```cypher
MATCH (p:Person {id: $person_id})
OPTIONAL MATCH (p)-[:CONNECTED_TO]->(direct:Person)
OPTIONAL MATCH (p)-[:CONNECTED_TO]->(:Person)-[:CONNECTED_TO]->(second:Person)
WHERE second IS NULL OR second <> p
RETURN count(DISTINCT direct) AS direct,
       count(DISTINCT second) AS second_degree,
       count(DISTINCT direct) + 0.5 * count(DISTINCT second) AS influence_score
```

## 6. Decision-makers по title

```cypher
MATCH (c:Company {domain: $domain})<-[:WORKS_AT]-(p:Person)
WHERE p.title =~ '(?i).*(CEO|CTO|CFO|COO|VP|Head|Director|Founder|Chief).*'
RETURN p ORDER BY p.title LIMIT $limit
```

## 7. Кого ещё не писали, но у кого есть связи

```cypher
MATCH (c:Company {domain: $domain})<-[:WORKS_AT]-(p:Person)
WHERE NOT (p)-[:PARTICIPATES_IN]->(:EmailThread)
OPTIONAL MATCH (p)-[:CONNECTED_TO]->(conn:Person)
WITH p, count(DISTINCT conn) AS connections_count
WHERE connections_count > 0
RETURN p, connections_count
ORDER BY connections_count DESC LIMIT $limit
```

## 8. Конкуренты + 5 людей

```cypher
MATCH (c:Company {domain: $domain})-[:COMPETITOR_OF]->(comp:Company)
OPTIONAL MATCH (comp)<-[:EMPLOYS]-(p:Person)
RETURN comp, collect(p)[..5] AS top_people
LIMIT $limit
```

## 9. Скрытые связи (коллега коллеги в целевой компании)

```cypher
MATCH (me:Person {id: $person_id})-[:CONNECTED_TO]->(bridge:Person)
      -[:CONNECTED_TO]->(target:Person)-[:WORKS_AT]->(c:Company {domain: $domain})
WHERE target <> me AND NOT (me)-[:CONNECTED_TO]-(target)
RETURN target, bridge LIMIT $limit
```

## 10. Счётчики графа

```cypher
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count
MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count
```

Connected components на этом железе: Python BFS по `CONNECTED_TO`, не `gds.wcc`.
