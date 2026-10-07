"""RAG-backed SEO article generation and persistence."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings as default_settings
from app.models.company import Company
from app.models.seo_article import SEOArticle
from app.schemas.article import ArticleGenerateRequest
from app.services.cost_tracker import CostTracker
from app.services.llm_client import LLMClient
from app.services.prompts.article_prompts import (
    ARTICLE_PROMPT_VERSION,
    SYSTEM_PROMPT_ARTICLE,
    USER_PROMPT_ARTICLE,
)
from app.services.rag_service import RAGService
from app.services.tracing import TracingService, get_tracing

_SLUG_BAD = re.compile(r"[^a-z0-9]+")
_SHORTENER_RE = re.compile(r"https?://(?:bit\.ly|t\.co|tinyurl\.com|goo\.gl)/", re.I)
_NO_CONTEXT_NOTICE = (
    "\n\n> Editorial note: company-specific claims require verification because no indexed "
    "research context was available."
)


class ArticleGenerator:
    """Retrieve company evidence, generate structured content, validate, and persist it."""

    def __init__(
        self,
        db: AsyncSession,
        settings: Settings | None = None,
        llm_client: LLMClient | None = None,
        rag_service: RAGService | None = None,
        cost_tracker: CostTracker | None = None,
        tracing: TracingService | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or default_settings
        self.cost_tracker = cost_tracker or CostTracker()
        self.tracing = tracing if tracing is not None else get_tracing()
        self.llm_client = llm_client or LLMClient(
            self.settings, cost_tracker=self.cost_tracker, tracing=self.tracing
        )
        self.rag_service = rag_service or RAGService(self.settings)

    async def generate(self, request: ArticleGenerateRequest) -> SEOArticle:
        """Generate and save a draft article for an existing company domain."""
        company = await self.db.scalar(
            select(Company).where(Company.domain == request.company_domain.lower())
        )
        if company is None:
            raise LookupError(f"Company '{request.company_domain}' not found")

        hits = await self._retrieve(company, request.keyword)
        context = "\n\n".join(str(hit["text"]) for hit in hits if hit.get("text"))
        has_context = bool(context)
        if not context:
            context = "No indexed company research is available."
        system = SYSTEM_PROMPT_ARTICLE.format(
            language=request.language, max_words=request.max_words
        )
        user = USER_PROMPT_ARTICLE.format(
            company_name=company.name,
            keyword=request.keyword,
            language=request.language,
            max_words=request.max_words,
            rag_context=context,
        )
        result = await self.llm_client.chat_json(
            system,
            user,
            max_tokens=min(3000, request.max_words * 2),
            extra_metadata={"prompt_version": ARTICLE_PROMPT_VERSION},
        )
        title, slug, body = self._validate_output(result["parsed"], request.max_words)
        if not has_context and _NO_CONTEXT_NOTICE.strip() not in body:
            body += _NO_CONTEXT_NOTICE
        record = self.cost_tracker.records[-1] if self.cost_tracker.records else None
        article = SEOArticle(
            company_id=company.id,
            title=title,
            slug=slug,
            body_markdown=body,
            language=request.language,
            status="draft",
            keywords=[],
            rag_context_used=hits,
            tokens_input=int(result["tokens_input"]),
            tokens_output=int(result["tokens_output"]),
            estimated_cost_usd=record.estimated_cost_usd if record else 0,
            generation_prompt_version=ARTICLE_PROMPT_VERSION,
            keyword_primary=request.keyword,
        )
        self.db.add(article)
        await self.db.commit()
        await self.db.refresh(article)
        return article

    async def _retrieve(self, company: Company, keyword: str) -> list[dict[str, Any]]:
        if not company.raw_site_text:
            return []
        try:
            return await self.rag_service.search(company.domain, keyword, top_k=5)
        except Exception:
            return []

    @staticmethod
    def _validate_output(parsed: dict[str, Any], max_words: int) -> tuple[str, str, str]:
        title = str(parsed.get("title") or "").strip()
        raw_slug = str(parsed.get("slug") or title).strip().lower()
        body = str(parsed.get("body_markdown") or "").strip()
        slug = _SLUG_BAD.sub("-", raw_slug).strip("-")[:300]
        if not title or not slug or not body:
            raise ValueError("LLM JSON must include non-empty title, slug, and body_markdown")
        if len(body.split()) > max_words:
            raise ValueError(f"Generated article exceeds {max_words} words")
        if _SHORTENER_RE.search(body):
            raise ValueError("Generated article contains a prohibited URL shortener")
        return title[:300], slug, body
