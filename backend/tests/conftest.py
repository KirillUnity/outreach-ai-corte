"""Shared fixtures for parser unit tests (no database, no network)."""

from collections.abc import Iterator

import httpx
import pytest

from app.core.config import ParserSettings, Settings


@pytest.fixture
def settings() -> Settings:
    """Tight limits so truncation tests stay fast."""
    return Settings(
        parser=ParserSettings(
            timeout=5,
            max_retries=0,
            max_text_length=80,
            follow_links=["/about"],
        )
    )


@pytest.fixture
def mock_html() -> str:
    return """
    <html>
      <head>
        <title>Acme Widgets</title>
        <meta name="description" content="We sell widgets.">
      </head>
      <body>
        <header>Nav ignore</header>
        <nav><a href="/about">About</a></nav>
        <h1>Welcome to Acme</h1>
        <p>Acme builds reliable widgets for teams.</p>
        <script>window.SECRET = "do-not-extract";</script>
        <footer>Copyright</footer>
      </body>
    </html>
    """


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: live API on http://127.0.0.1:8080")


@pytest.fixture
def api_client() -> Iterator[httpx.Client]:
    """HTTP client for Docker integration tests; skip when the API is down."""
    try:
        httpx.get("http://127.0.0.1:8080/api/v1/health", timeout=2.0)
    except httpx.HTTPError:
        pytest.skip("API not running at :8080")
    with httpx.Client(base_url="http://127.0.0.1:8080", timeout=60.0) as client:
        yield client
