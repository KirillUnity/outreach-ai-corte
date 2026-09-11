"""Fetch and extract readable text from a company website."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

import httpx
import trafilatura
from bs4 import BeautifulSoup, Tag

from app.core.config import Settings, settings as default_settings

logger = logging.getLogger(__name__)

_RETRY_BACKOFF = (0.5, 1.0, 2.0)
_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"}


@dataclass
class ParseResult:
    """Outcome of a site crawl. Always returned — never raised for fetch failures."""

    domain: str
    title: str = ""
    description: str = ""
    raw_text: str = ""
    pages_parsed: int = 0
    errors: list[str] = field(default_factory=list)


class SiteParser:
    """Async homepage + a few product/about paths. Safe to call when the site is down."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or default_settings

    async def fetch_page(self, url: str) -> str | None:
        """GET html with retries. Returns None on timeout, HTTP errors, or non-HTML."""
        cfg = self.settings.parser
        timeout = httpx.Timeout(cfg.timeout)
        headers = {"User-Agent": cfg.user_agent}
        last_error = "unknown error"

        for attempt in range(cfg.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=timeout,
                    follow_redirects=True,
                    headers=headers,
                ) as client:
                    response = await client.get(url)
            except httpx.TimeoutException as exc:
                last_error = f"timeout: {exc}"
                logger.warning("fetch timeout url=%s attempt=%s error=%s", url, attempt + 1, exc)
            except httpx.HTTPError as exc:
                last_error = f"http error: {exc}"
                logger.warning("fetch http error url=%s attempt=%s error=%s", url, attempt + 1, exc)
            else:
                if response.status_code == 404:
                    logger.info("fetch 404 url=%s", url)
                    return None
                if response.status_code in {429, 500, 502, 503, 504}:
                    last_error = f"HTTP {response.status_code}"
                    logger.warning(
                        "fetch retryable status url=%s status=%s attempt=%s",
                        url,
                        response.status_code,
                        attempt + 1,
                    )
                elif not response.is_success:
                    last_error = f"HTTP {response.status_code}"
                    logger.warning("fetch failed url=%s status=%s", url, response.status_code)
                    return None
                else:
                    content_type = response.headers.get("content-type", "").lower()
                    if content_type and "html" not in content_type and "text/" not in content_type:
                        logger.info("skip non-html url=%s content_type=%s", url, content_type)
                        return None
                    return response.text

            if attempt < cfg.max_retries:
                delay = _RETRY_BACKOFF[min(attempt, len(_RETRY_BACKOFF) - 1)]
                await asyncio.sleep(delay)

        logger.error("fetch gave up url=%s last_error=%s", url, last_error)
        return None

    async def extract_text(self, html: str) -> str:
        """Prefer trafilatura; fall back to a stripped BeautifulSoup walk."""
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
        )
        text = (extracted or "").strip() or self._bs4_extract(html)
        max_len = self.settings.parser.max_text_length
        if len(text) > max_len:
            text = text[:max_len].rsplit(" ", maxsplit=1)[0]
        return text.strip()

    async def parse_company_site(self, domain: str) -> ParseResult:
        """Crawl https://{domain} plus follow_links. Never raises on network failure."""
        result = ParseResult(domain=domain)
        if not self._is_safe_host(domain):
            result.errors.append(f"refusing to fetch blocked host: {domain}")
            logger.warning("ssrf guard blocked domain=%s", domain)
            return result

        home_url = f"https://{domain}"
        html = await self.fetch_page(home_url)
        if html is None:
            result.errors.append(f"failed to fetch {home_url}")
            logger.warning("homepage unavailable domain=%s", domain)
            return result

        title, description = self._meta(html)
        result.title = title
        result.description = description
        chunks: list[str] = []
        home_text = await self.extract_text(html)
        if home_text:
            chunks.append(home_text)
        result.pages_parsed += 1

        for path in self.settings.parser.follow_links:
            normalized = path if path.startswith("/") else f"/{path}"
            page_url = f"https://{domain}{normalized}"
            page_html = await self.fetch_page(page_url)
            if page_html is None:
                result.errors.append(f"failed to fetch {page_url}")
                continue
            page_text = await self.extract_text(page_html)
            if page_text:
                chunks.append(page_text)
            result.pages_parsed += 1

        combined = "\n\n".join(chunks)
        max_len = self.settings.parser.max_text_length
        if len(combined) > max_len:
            combined = combined[:max_len].rsplit(" ", maxsplit=1)[0]
        result.raw_text = combined.strip()
        logger.info(
            "parsed domain=%s pages=%s errors=%s chars=%s",
            domain,
            result.pages_parsed,
            len(result.errors),
            len(result.raw_text),
        )
        return result

    def _bs4_extract(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()
        parts: list[str] = []
        for el in soup.find_all(["p", "h1", "h2", "h3", "li"]):
            if not isinstance(el, Tag):
                continue
            text = el.get_text(" ", strip=True)
            if text:
                parts.append(text)
        return "\n".join(parts)

    def _meta(self, html: str) -> tuple[str, str]:
        soup = BeautifulSoup(html, "lxml")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        description = ""
        meta = soup.find("meta", attrs={"name": "description"})
        if isinstance(meta, Tag):
            content = meta.get("content")
            if isinstance(content, str):
                description = content.strip()
        return title, description

    @staticmethod
    def _is_safe_host(domain: str) -> bool:
        """Block obvious local/metadata hosts. Callers must pass a hostname, not a URL."""
        host = domain.strip().lower().split(":")[0]
        return host not in _BLOCKED_HOSTS and not host.endswith(".local")
