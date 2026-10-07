"""Deterministic SEO metadata and internal-link optimization."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.seo_article import SEOArticle
from app.services.llm_client import LLMClient

_WORDS = re.compile(r"[^\W\d_]{4,}", re.UNICODE)
_STOP = {"this", "that", "with", "from", "have", "your", "для", "или", "как", "что", "это"}


class SeoOptimizer:
    """Populate conservative SEO fields without an LLM by default."""

    def __init__(self, db: AsyncSession, llm_client: LLMClient | None = None) -> None:
        self.db = db
        self.llm_client = llm_client or LLMClient()

    async def optimize(self, article: SEOArticle, use_llm: bool = False) -> SEOArticle:
        """Optimize and persist metadata and safe same-company links."""
        company = (
            await self.db.get(Company, article.company_id) if article.company_id is not None else None
        )
        first_paragraph = self._first_paragraph(article.body_markdown)
        primary = article.keyword_primary or article.title
        article.meta_title = self._truncate(article.title, 60)
        article.meta_description = self._truncate(first_paragraph, 160)
        article.keywords = self._keywords(primary, article.rag_context_used)
        article.internal_links = await self._internal_links(article, company)
        if use_llm:
            await self._apply_llm(article)
        await self.db.commit()
        await self.db.refresh(article)
        return article

    async def _internal_links(
        self, article: SEOArticle, company: Company | None
    ) -> list[dict[str, str]]:
        if company is None:
            return []
        links = [{"anchor": company.name, "url": f"https://{company.domain}"}]
        others = list(
            (
                await self.db.scalars(
                    select(SEOArticle)
                    .where(
                        SEOArticle.company_id == company.id,
                        SEOArticle.id != article.id,
                    )
                    .order_by(SEOArticle.created_at.desc())
                    .limit(2)
                )
            ).all()
        )
        links.extend(
            {"anchor": other.title, "url": f"/articles/{other.slug}"} for other in others
        )
        return links[:3]

    async def _apply_llm(self, article: SEOArticle) -> None:
        result = await self.llm_client.chat_json(
            "Return JSON keys meta_title, meta_description, keywords. Do not add URLs.",
            f"Title: {article.title}\nText: {article.body_markdown[:2000]}",
            max_tokens=300,
        )
        parsed: dict[str, Any] = result["parsed"]
        if parsed.get("meta_title"):
            article.meta_title = self._truncate(str(parsed["meta_title"]), 60)
        if parsed.get("meta_description"):
            article.meta_description = self._truncate(str(parsed["meta_description"]), 160)
        if isinstance(parsed.get("keywords"), list):
            article.keywords = list(dict.fromkeys(str(x).strip() for x in parsed["keywords"] if x))[
                :8
            ]

    @staticmethod
    def _keywords(primary: str, context: list[dict[str, object]]) -> list[str]:
        text = " ".join(str(chunk.get("text") or "") for chunk in context)
        counts = Counter(
            word.lower() for word in _WORDS.findall(text) if word.lower() not in _STOP
        )
        candidates = [primary.strip()] + [word for word, _ in counts.most_common(7)]
        return list(dict.fromkeys(item for item in candidates if item))[:8]

    @staticmethod
    def _first_paragraph(markdown: str) -> str:
        paragraphs = [
            line.strip().lstrip("#").strip()
            for line in markdown.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]
        return paragraphs[0] if paragraphs else markdown.strip().lstrip("#").strip()

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        value = " ".join(value.split())
        if len(value) <= limit:
            return value
        return value[: limit - 1].rstrip() + "…"
