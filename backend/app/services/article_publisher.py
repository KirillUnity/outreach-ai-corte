"""Idempotent mock or webhook article publishing."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings as default_settings
from app.models.seo_article import SEOArticle


class ArticlePublisher:
    """Publish articles through a safe demo channel or configured webhook."""

    def __init__(
        self,
        db: AsyncSession,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or default_settings
        self._client = client

    async def publish(self, article_id: UUID) -> SEOArticle:
        """Publish once; an already published article is an idempotent no-op."""
        article = await self.db.get(SEOArticle, article_id)
        if article is None:
            raise LookupError("Article not found")
        if article.status == "published":
            return article
        if article.status not in {"draft", "ready", "scheduled", "failed"}:
            raise ValueError(f"Article in status '{article.status}' cannot be published")

        if article.publish_channel == "webhook":
            try:
                await self._publish_webhook(article)
            except Exception:
                article.status = "failed"
                await self.db.commit()
                raise
        else:
            article.status = "published"
            article.published_at = datetime.now(UTC)
            article.publish_url = f"https://example.invalid/posts/{article.slug}"
        await self.db.commit()
        await self.db.refresh(article)
        return article

    async def tick_due(self, now: datetime | None = None) -> tuple[int, int, int]:
        """Publish all due scheduled articles and report processed/published/failed."""
        current = now or datetime.now(UTC)
        due = list(
            (
                await self.db.scalars(
                    select(SEOArticle).where(
                        SEOArticle.status == "scheduled",
                        SEOArticle.scheduled_at <= current,
                    )
                )
            ).all()
        )
        published = 0
        failed = 0
        for article in due:
            try:
                await self.publish(article.id)
                published += 1
            except Exception:
                article.status = "failed"
                await self.db.commit()
                failed += 1
        return len(due), published, failed

    async def schedule(self, article_id: UUID, scheduled_at: datetime) -> SEOArticle:
        """Move an unpublished article into the scheduled queue."""
        article = await self.db.get(SEOArticle, article_id)
        if article is None:
            raise LookupError("Article not found")
        if article.status == "published":
            raise ValueError("Published articles cannot be scheduled")
        article.status = "scheduled"
        article.scheduled_at = scheduled_at
        await self.db.commit()
        await self.db.refresh(article)
        return article

    async def _publish_webhook(self, article: SEOArticle) -> None:
        url = self.settings.content.publish_webhook_url
        if not url:
            article.status = "failed"
            raise ValueError("CONTENT_PUBLISH_WEBHOOK_URL is not configured")
        payload = {
            "title": article.title,
            "slug": article.slug,
            "body": article.body_markdown,
        }
        if self._client is not None:
            response = await self._client.post(url, json=payload)
        else:
            async with httpx.AsyncClient(timeout=self.settings.content.timeout_seconds) as client:
                response = await client.post(url, json=payload)
        if not 200 <= response.status_code < 300:
            article.status = "failed"
            raise RuntimeError(f"Publish webhook returned HTTP {response.status_code}")
        article.status = "published"
        article.published_at = datetime.now(UTC)
        article.publish_url = response.headers.get("Location") or url
