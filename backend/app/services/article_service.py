"""SEO article CRUD operations."""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.seo_article import SEOArticle
from app.schemas.article import ArticleCreate, ArticleUpdate
from app.services.prompts.article_prompts import ARTICLE_PROMPT_VERSION


class ArticleService:
    """Persist and query articles without HTTP concerns."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: ArticleCreate) -> SEOArticle:
        """Create a manually authored draft."""
        article = SEOArticle(
            **data.model_dump(),
            status="draft",
            generation_prompt_version=f"{ARTICLE_PROMPT_VERSION}-manual",
        )
        self.db.add(article)
        await self.db.commit()
        await self.db.refresh(article)
        return article

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        company_id: UUID | None = None,
        status: str | None = None,
    ) -> tuple[list[SEOArticle], int]:
        """Return filtered articles and total count."""
        filters = []
        if company_id is not None:
            filters.append(SEOArticle.company_id == company_id)
        if status is not None:
            filters.append(SEOArticle.status == status)
        query = (
            select(SEOArticle)
            .where(*filters)
            .order_by(SEOArticle.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        count_query = select(func.count()).select_from(SEOArticle).where(*filters)
        return list((await self.db.scalars(query)).all()), int(
            (await self.db.scalar(count_query)) or 0
        )

    async def get(self, article_id: UUID) -> SEOArticle | None:
        """Fetch one article."""
        return await self.db.get(SEOArticle, article_id)

    async def update(self, article_id: UUID, data: ArticleUpdate) -> SEOArticle | None:
        """Apply operator-editable fields."""
        article = await self.get(article_id)
        if article is None:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(article, key, value)
        await self.db.commit()
        await self.db.refresh(article)
        return article

    async def delete(self, article_id: UUID) -> bool:
        """Delete an article by id."""
        result = await self.db.execute(delete(SEOArticle).where(SEOArticle.id == article_id))
        await self.db.commit()
        return bool(result.rowcount)
