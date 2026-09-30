"""Central Cypher library. Variable-length hops cannot take `$params` — use *1..6."""

# --- networks ---
QUERY_COMPANY_NETWORK = """
MATCH (c:Company {domain: $domain})
OPTIONAL MATCH (c)<-[:WORKS_AT]-(p:Person)
RETURN c {.*} AS company, p {.*} AS person
LIMIT $limit
"""

QUERY_COMPANY_NETWORK_DEPTH2 = """
MATCH (c:Company {domain: $domain})<-[:WORKS_AT]-(p:Person)
OPTIONAL MATCH (p)-[:CONNECTED_TO]-(friend:Person)
OPTIONAL MATCH (friend)-[:WORKS_AT]->(fc:Company)
RETURN p {.*} AS person, friend {.*} AS friend, fc {.*} AS friend_company
LIMIT $limit
"""

QUERY_PERSON_NETWORK = """
MATCH (p:Person {id: $person_id})
OPTIONAL MATCH (p)-[:WORKS_AT]->(c:Company)
OPTIONAL MATCH (p)-[:CONNECTED_TO]->(other:Person)
OPTIONAL MATCH (p)-[:PARTICIPATES_IN]->(t:EmailThread)
RETURN p {.*} AS person, c {.*} AS company, other {.*} AS other, t {.*} AS thread
LIMIT $limit
"""

QUERY_SHORTEST_PATH = """
MATCH (a:Person {id: $from_id}), (b:Person {id: $to_id})
MATCH path = shortestPath((a)-[:CONNECTED_TO*1..6]-(b))
RETURN [node IN nodes(path) | {
    id: node.id,
    name: coalesce(node.first_name, '') + ' ' + coalesce(node.last_name, ''),
    title: node.title
}] AS path,
length(path) AS distance
"""

QUERY_MUTUAL_CONNECTIONS = """
MATCH (a:Person {id: $person_a_id})-[:CONNECTED_TO]->(mutual:Person)<-[:CONNECTED_TO]-(b:Person {id: $person_b_id})
WHERE a <> b
RETURN DISTINCT mutual {.*} AS mutual
LIMIT $limit
"""

QUERY_FRIENDS_AT_COMPANY = """
MATCH (me:Person {id: $person_id})-[:CONNECTED_TO]-(friend:Person)-[:WORKS_AT]->(c:Company {id: $company_id})
RETURN friend {.*} AS person, c {.*} AS company, 1 AS connection_path_length
LIMIT $limit
"""

QUERY_INFLUENCE_SCORE = """
MATCH (p:Person {id: $person_id})
OPTIONAL MATCH (p)-[:CONNECTED_TO]->(direct:Person)
OPTIONAL MATCH (p)-[:CONNECTED_TO]->(:Person)-[:CONNECTED_TO]->(second:Person)
WHERE second IS NULL OR second <> p
WITH p,
     count(DISTINCT direct) AS direct_connections,
     count(DISTINCT second) AS second_degree_connections
RETURN p.id AS id,
       direct_connections,
       second_degree_connections,
       (direct_connections * 1.0) + (second_degree_connections * 0.5) AS influence_score
"""

QUERY_ALL_INFLUENCE = """
MATCH (p:Person)
OPTIONAL MATCH (p)-[:CONNECTED_TO]->(direct:Person)
OPTIONAL MATCH (p)-[:CONNECTED_TO]->(:Person)-[:CONNECTED_TO]->(second:Person)
WHERE second IS NULL OR second <> p
WITH p,
     count(DISTINCT direct) AS direct_connections,
     count(DISTINCT second) AS second_degree_connections
RETURN p.id AS id,
       coalesce(p.first_name, '') + ' ' + coalesce(p.last_name, '') AS name,
       direct_connections,
       second_degree_connections,
       (direct_connections * 1.0) + (second_degree_connections * 0.5) AS influence_score
ORDER BY influence_score DESC
LIMIT $limit
"""

QUERY_COMPANY_COMPETITORS = """
MATCH (c:Company {domain: $domain})-[:COMPETITOR_OF]->(comp:Company)
OPTIONAL MATCH (comp)<-[:EMPLOYS]-(p:Person)
RETURN comp {.*} AS competitor, collect(p {.*})[..5] AS top_people
LIMIT $limit
"""

QUERY_DECISION_MAKERS_AT_COMPANY = """
MATCH (c:Company {domain: $domain})<-[:WORKS_AT]-(p:Person)
WHERE p.title =~ '(?i).*(CEO|CTO|CFO|COO|VP|Head|Director|Founder|Chief).*'
RETURN p {.*} AS person
ORDER BY p.title
LIMIT $limit
"""

QUERY_RECOMMEND_OUTREACH_TARGETS = """
MATCH (c:Company {domain: $domain})<-[:WORKS_AT]-(p:Person)
WHERE NOT (p)-[:PARTICIPATES_IN]->(:EmailThread)
OPTIONAL MATCH (p)-[:CONNECTED_TO]->(conn:Person)
WITH p, c, count(DISTINCT conn) AS connections_count
WHERE connections_count > 0
RETURN p {.*} AS person, connections_count
ORDER BY connections_count DESC
LIMIT $limit
"""

QUERY_PATH_TO_COMPANY = """
MATCH (a:Person {id: $person_id}), (c:Company {domain: $domain})<-[:WORKS_AT]-(target:Person)
MATCH path = shortestPath((a)-[:CONNECTED_TO*1..6]-(target))
RETURN [node IN nodes(path) | {
    id: node.id,
    name: coalesce(node.first_name, '') + ' ' + coalesce(node.last_name, '')
}] AS path,
target {.*} AS target,
length(path) AS distance
ORDER BY distance ASC
LIMIT 1
"""

QUERY_ADD_COMPETITOR = """
MATCH (a:Company {domain: $a}), (b:Company {domain: $b})
MERGE (a)-[r1:COMPETITOR_OF]->(b)
MERGE (b)-[r2:COMPETITOR_OF]->(a)
SET r1.created_at = datetime(), r2.created_at = datetime()
RETURN a.domain AS a, b.domain AS b
"""

QUERY_AUTO_DETECT_COMPETITORS = """
MATCH (c:Company {domain: $domain}), (other:Company)
WHERE other.industry = $industry AND other.domain <> $domain
RETURN other.domain AS domain, other.name AS name
LIMIT 10
"""

QUERY_UNCONTACTED_AT_COMPANY = """
MATCH (c:Company {domain: $domain})<-[:WORKS_AT]-(p:Person)
WHERE NOT (p)-[:PARTICIPATES_IN]->(:EmailThread)
RETURN p {.*} AS person
LIMIT $limit
"""

QUERY_UNCONTACTED_GLOBAL = """
MATCH (p:Person)
WHERE NOT (p)-[:PARTICIPATES_IN]->(:EmailThread)
OPTIONAL MATCH (p)-[:CONNECTED_TO]->(conn:Person)
WITH p, count(DISTINCT conn) AS connections_count
RETURN p {.*} AS person, connections_count
ORDER BY connections_count DESC
LIMIT $limit
"""

QUERY_HIDDEN_CONNECTIONS = """
MATCH (me:Person {id: $person_id})-[:CONNECTED_TO]->(bridge:Person)-[:CONNECTED_TO]->(target:Person)-[:WORKS_AT]->(c:Company {domain: $domain})
WHERE target <> me AND NOT (me)-[:CONNECTED_TO]-(target)
RETURN target {.*} AS target, bridge {.*} AS bridge, c {.*} AS company
LIMIT $limit
"""

QUERY_WARM_INTRO_CANDIDATES = """
MATCH (sender:Person {id: $sender_id})
MATCH (target_company:Company {domain: $target_domain})<-[:WORKS_AT]-(target:Person)
WHERE target.id <> sender.id
  AND NOT (target)-[:PARTICIPATES_IN]->(:EmailThread)
OPTIONAL MATCH path = shortestPath((sender)-[:CONNECTED_TO*1..6]-(target))
WITH sender, target, target_company, path
OPTIONAL MATCH (sender)-[:CONNECTED_TO]->(mutual:Person)<-[:CONNECTED_TO]-(target)
WITH sender, target, target_company, path,
     count(DISTINCT mutual) AS mutual_connections
OPTIONAL MATCH (target)-[:CONNECTED_TO]->(direct:Person)
OPTIONAL MATCH (target)-[:CONNECTED_TO]->(:Person)-[:CONNECTED_TO]->(second:Person)
WHERE second IS NULL OR second <> target
WITH sender, target, target_company, path, mutual_connections,
     count(DISTINCT direct) AS direct_connections,
     count(DISTINCT second) AS second_degree
RETURN
    target {.*} AS target,
    target_company {.*} AS company,
    CASE WHEN path IS NULL THEN [] ELSE [node IN nodes(path) | {
        id: node.id,
        name: coalesce(node.first_name, '') + ' ' + coalesce(node.last_name, ''),
        title: node.title
    }] END AS path_nodes,
    CASE WHEN path IS NULL THEN -1 ELSE length(path) END AS distance,
    mutual_connections,
    (direct_connections * 1.0) + (second_degree * 0.5) AS influence_score
ORDER BY
    CASE WHEN path IS NULL THEN 999 ELSE length(path) END ASC,
    influence_score DESC
LIMIT $limit
"""

QUERY_NODE_COUNTS = """
MATCH (n)
RETURN labels(n)[0] AS label, count(n) AS count
"""

QUERY_REL_COUNTS = """
MATCH ()-[r]->()
RETURN type(r) AS type, count(r) AS count
"""

QUERY_COMPANY_RANKINGS = """
MATCH (c:Company)
OPTIONAL MATCH (c)<-[:WORKS_AT]-(p:Person)
OPTIONAL MATCH (c)-[:COMPETITOR_OF]->(comp:Company)
RETURN c.domain AS domain, c.name AS name,
       count(DISTINCT p) AS employees,
       count(DISTINCT comp) AS competitors
ORDER BY employees DESC
LIMIT $limit
"""

QUERY_CONNECTION_EDGES = """
MATCH (a:Person)-[:CONNECTED_TO]-(b:Person)
WHERE a.id < b.id
RETURN a.id AS a, b.id AS b
LIMIT 5000
"""

QUERY_ADD_CONNECTION = """
MATCH (a:Person {id: $a_id}), (b:Person {id: $b_id})
MERGE (a)-[r1:CONNECTED_TO]->(b)
MERGE (b)-[r2:CONNECTED_TO]->(a)
SET r1.context = $context, r2.context = $context, r1.created_at = datetime()
RETURN a.id AS a, b.id AS b
"""
