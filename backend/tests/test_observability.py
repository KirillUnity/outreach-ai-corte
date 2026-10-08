"""Sentry stays off without a DSN. /metrics is plain text and avoids person labels."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers.metrics import router as metrics_router
from app.core.config import Settings, settings
from app.services.metrics import PrometheusMiddleware, note_agent_run, path_label, render_metrics
from app.services.sentry_setup import configure_sentry, scrub_pii


def _client() -> TestClient:
    app = FastAPI()
    app.add_middleware(PrometheusMiddleware)
    app.include_router(metrics_router)

    @app.get("/persons/{person_id}")
    def _person(person_id: str) -> dict[str, str]:
        return {"id": person_id}

    return TestClient(app)


def test_metrics_returns_200(monkeypatch) -> None:
    monkeypatch.setattr(settings, "prometheus_enabled", True)
    client = _client()
    person_id = "11111111-1111-1111-1111-111111111111"
    assert client.get(f"/persons/{person_id}").status_code == 200
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "http_requests_total" in body
    assert "http_request_duration_seconds" in body
    assert "/persons/{person_id}" in body
    assert person_id not in body


def test_metrics_disabled_is_stable(monkeypatch) -> None:
    monkeypatch.setattr(settings, "prometheus_enabled", False)
    client = _client()
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == "# prometheus metrics disabled\n"
    assert "http_requests_total" not in response.text


def test_path_label_drops_raw_path() -> None:
    assert path_label({"type": "http", "path": "/persons/ada@stripe.com"}) == "unmatched"


def test_agent_run_gauge_uses_decision_bucket(monkeypatch) -> None:
    monkeypatch.setattr(settings, "prometheus_enabled", True)
    note_agent_run("hold")
    body = render_metrics()[0].decode()
    assert 'agent_runs_total{decision="hold"}' in body
    for line in body.splitlines():
        if line.startswith("agent_runs_total{"):
            assert "person" not in line
            assert "@" not in line


def test_sentry_disabled_does_not_crash() -> None:
    assert configure_sentry(Settings(sentry_dsn="", sentry_enabled=False)) is False
    assert configure_sentry(Settings(sentry_dsn="", sentry_enabled=True)) is False
    assert (
        configure_sentry(
            Settings(sentry_dsn="https://public@o0.ingest.sentry.io/1", sentry_enabled=False)
        )
        is False
    )


def test_sentry_init_samples_prod_and_scrubs(monkeypatch) -> None:
    import sentry_sdk

    captured: dict = {}

    def fake_init(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(sentry_sdk, "init", fake_init)
    enabled = configure_sentry(
        Settings(
            sentry_dsn="https://public@o0.ingest.sentry.io/1",
            sentry_enabled=True,
            debug=False,
        )
    )
    assert enabled is True
    assert captured["traces_sample_rate"] == 0.1
    assert captured["send_default_pii"] is False
    before_send = captured["before_send"]
    assert callable(before_send)
    event = before_send(
        {
            "message": "reach ada@stripe.com at +1 415 555 0133",
            "user": {"email": "ada@stripe.com"},
        },
        {},
    )
    text = str(event)
    assert "ada@stripe.com" not in text
    assert "415" not in text
    assert "[redacted-email]" in text


def test_scrub_pii_standalone() -> None:
    cleaned = scrub_pii({"logentry": {"message": "ping ada@example.com"}}, None)
    assert cleaned is not None
    assert "ada@example.com" not in str(cleaned)
