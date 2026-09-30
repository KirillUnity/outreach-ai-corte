# Warm intro path finding

## Problem

Cold email is colder when you already share a path in the relationship graph. The product question is: **who at this account can we reach through someone we already know, and who is worth the intro?**

## Approach

1. In Neo4j, `shortestPath` on `CONNECTED_TO` from sender to uncontacted people at the target `Company`.
2. Count mutual `CONNECTED_TO` neighbors.
3. Score influence as `direct + 0.5 * second_degree` (no GDS PageRank on 8 GB RAM).
4. Sort by **distance ASC**, then **influence DESC**.
5. Drop people with `PARTICIPATES_IN` an `EmailThread` — they are already in the funnel.

Hop cap is `*1..6` in Cypher (`$max_depth` cannot expand variable-length patterns). The HTTP `max_depth` query param filters after the query.

## Ranking heuristic

`priority ≈ -distance * 10 + influence_score`

Distance dominates: a 1-hop intro beats a high-degree VP six hops away. Influence is a tie-break among equal hop counts. This is a **heuristic**, not a causal model of reply rate.

## What to improve

- Industry / title match between sender and target
- Recency of last `CONNECTED_TO` context
- PageRank only if GDS and RAM allow it
- A/B on reply rate: warm-intro prompt vs generic RAG prompt

## API / UI

- `GET /api/v1/graph/warm-intro/search?sender_person_id=&target_company_domain=`
- UI: `/warm-intro`
- Agent node `enrich_with_graph` feeds `USER_PROMPT_WITH_WARM_INTRO` when a named mutual exists
