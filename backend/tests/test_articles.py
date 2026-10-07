"""Unit tests for article generation, publishing, and deterministic SEO."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.company import Company
from app.models.seo_article import SEOArticle
from app.schemas.article import ArticleGenerateRequest
from app.services.article_generator import ArticleGenerator
from app.services.article_publisher import ArticlePublisher
from app.services.seo_optimizer import SeoOptimizer


class FakeSession:
    """Small async-session stand-in for service units."""

    def __init__(self, company: Company | None = None, article: SEOArticle | None = None) -> None:
        self.company = company
        self.article = article
        self.added: list[object] = []
        self.commit = AsyncMock()
        self.refresh = AsyncMock()

    async def scalar(self, _query: object) -> object | None:
        return self.company

    async def get(self, model: object, _object_id: object) -> object | None:
        if model is Company:
            return self.company
        return self.article

    def add(self, value: object) -> None:
        self.added.append(value)


def make_article(**overrides: object) -> SEOArticle:
    data = {
        "id": uuid4(),
        "company_id": uuid4(),
        "title": "A useful title",
        "slug": "a-useful-title",
        "body_markdown": "# A useful title\n\nA concise first paragraph about outreach.",
        "language": "en",
        "status": "draft",
        "keywords": [],
        "rag_context_used": [],
        "tokens_input": 0,
        "tokens_output": 0,
        "estimated_cost_usd": 0,
        "generation_prompt_version": "article-v1",
        "publish_channel": "mock",
        "internal_links": [],
    }
    data.update(overrides)
    return SEOArticle(**data)


@pytest.mark.asyncio
async def test_generate_persists_article() -> None:
    company = Company(id=uuid4(), domain="acme.test", name="Acme", raw_site_text="facts")
    session = FakeSession(company=company)
    llm = SimpleNamespace(
        chat_json=AsyncMock(
            return_value={
                "parsed": {
                    "title": "Verified outreach",
                    "slug": "verified-outreach",
                    "body_markdown": "# Verified outreach\n\nOnly supplied facts.",
                },
                "tokens_input": 10,
                "tokens_output": 20,
                "model": "mock",
            }
        )
    )
    rag = SimpleNamespace(
        search=AsyncMock(return_value=[{"text": "Acme builds outreach software", "score": 1.0}])
    )
    article = await ArticleGenerator(
        session, llm_client=llm, rag_service=rag
    ).generate(ArticleGenerateRequest(company_domain="acme.test", keyword="outreach"))
    assert article.status == "draft"
    assert article.rag_context_used
    assert session.added == [article]
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_rag_still_draft_with_disclaimer() -> None:
    company = Company(id=uuid4(), domain="empty.test", name="Empty", raw_site_text=None)
    session = FakeSession(company=company)
    llm = SimpleNamespace(
        chat_json=AsyncMock(
            return_value={
                "parsed": {
                    "title": "Editorial draft",
                    "slug": "editorial-draft",
                    "body_markdown": "# Editorial draft\n\nGeneral guidance only.",
                },
                "tokens_input": 1,
                "tokens_output": 2,
                "model": "mock",
            }
        )
    )
    article = await ArticleGenerator(session, llm_client=llm).generate(
        ArticleGenerateRequest(company_domain="empty.test", keyword="research")
    )
    assert article.status == "draft"
    assert "require" in article.body_markdown.lower()


@pytest.mark.asyncio
async def test_slug_unique_conflict_is_preserved() -> None:
    company = Company(id=uuid4(), domain="acme.test", name="Acme")
    session = FakeSession(company=company)
    session.commit.side_effect = IntegrityError("insert", {}, Exception("unique"))
    with pytest.raises(IntegrityError):
        await ArticleGenerator(session).generate(
            ArticleGenerateRequest(company_domain="acme.test", keyword="outreach")
        )


@pytest.mark.asyncio
async def test_mock_publish_is_idempotent() -> None:
    article = make_article()
    session = FakeSession(article=article)
    publisher = ArticlePublisher(session)
    first = await publisher.publish(article.id)
    published_at = first.published_at
    second = await publisher.publish(article.id)
    assert second.status == "published"
    assert second.publish_url == "https://example.invalid/posts/a-useful-title"
    assert second.published_at == published_at
    assert session.commit.await_count == 1


@pytest.mark.asyncio
async def test_tick_due_does_not_touch_future() -> None:
    future = make_article(
        status="scheduled", scheduled_at=datetime.now(UTC) + timedelta(hours=1)
    )
    session = FakeSession(article=future)
    session.scalars = AsyncMock(return_value=SimpleNamespace(all=lambda: []))
    processed, published, failed = await ArticlePublisher(session).tick_due()
    assert (processed, published, failed) == (0, 0, 0)
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_seo_meta_lengths_and_links_are_controlled() -> None:
    company = Company(id=uuid4(), domain="acme.test", name="Acme")
    article = make_article(
        company_id=company.id,
        title="A" * 100,
        body_markdown="# Heading\n\n" + "Useful description " * 30,
    )
    session = FakeSession(company=company, article=article)
    session.scalars = AsyncMock(return_value=SimpleNamespace(all=lambda: []))
    optimized = await SeoOptimizer(session).optimize(article)
    assert len(optimized.meta_title or "") <= 60
    assert len(optimized.meta_description or "") <= 160
    assert all(
        link["url"] == "https://acme.test" or link["url"].startswith("/articles/")
        for link in optimized.internal_links
    )
