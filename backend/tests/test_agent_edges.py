"""Routing functions — no I/O, no LangGraph."""

from uuid import uuid4

from app.services.agent.edges import route_after_decide, route_after_load, route_after_validate


def _base(**kwargs):
    state = {
        "person_id": uuid4(),
        "goal": "meeting",
        "sender_name": "Kirill",
        "sender_title": "Founder",
        "sender_company": "AI Cortex",
        "language": "en",
        "max_words": 120,
        "iteration": 0,
        "total_tokens_input": 0,
        "total_tokens_output": 0,
        "total_cost_usd": 0.0,
        "validation_errors": [],
        "errors": [],
    }
    state.update(kwargs)
    return state


def test_route_after_load_with_errors() -> None:
    assert route_after_load(_base(errors=["Person missing"])) == "fail"


def test_route_after_validate_with_errors_low_iteration() -> None:
    assert (
        route_after_validate(_base(validation_errors=["spam"], iteration=1)) == "generate_email"
    )


def test_route_after_validate_with_errors_high_iteration() -> None:
    assert (
        route_after_validate(_base(validation_errors=["spam"], iteration=2))
        == "check_deliverability"
    )


def test_route_after_decide_send() -> None:
    assert route_after_decide(_base(decision="send")) == "save_and_send"


def test_route_after_decide_hold() -> None:
    assert route_after_decide(_base(decision="hold")) == "save_draft"
