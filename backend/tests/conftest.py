"""Shared fixtures for parser unit tests (no database, no network)."""

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
