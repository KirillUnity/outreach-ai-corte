"""Cypher library shape — no Bolt."""

from app.services.graph import queries as cypher


def test_shortest_path_query_format() -> None:
    assert "shortestPath" in cypher.QUERY_SHORTEST_PATH
    assert "*1..6" in cypher.QUERY_SHORTEST_PATH
    assert "$max_depth" not in cypher.QUERY_SHORTEST_PATH


def test_influence_score_formula() -> None:
    direct, second = 2, 4
    score = (direct * 1.0) + (second * 0.5)
    assert score == 4.0
    assert "direct_connections * 1.0" in cypher.QUERY_INFLUENCE_SCORE
    assert "second_degree_connections * 0.5" in cypher.QUERY_INFLUENCE_SCORE
