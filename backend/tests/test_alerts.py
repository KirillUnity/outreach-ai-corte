"""AlertsService threshold checks."""

from app.services.agent.alerts import AlertsService


def test_check_cost_threshold_warns_when_over() -> None:
    alerts = AlertsService()
    assert alerts.check_cost_threshold(1.5, threshold=1.0) is True
    assert alerts.check_cost_threshold(0.2, threshold=1.0) is False


def test_check_error_rate_needs_sample() -> None:
    alerts = AlertsService()
    assert alerts.check_error_rate(1, 1, threshold=0.1) is False
    assert alerts.check_error_rate(2, 10, threshold=0.1) is True
    assert alerts.check_error_rate(0, 10, threshold=0.1) is False
