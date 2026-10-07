"""Thin HTTP endpoints for article generation, editing, SEO, and publishing."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_settings
from app.core.config import Settings
from app.schemas.article import (
    ArticleCreate,
    ArticleGenerateRequest,
    ArticleListResponse,
    ArticleResponse,
    ArticleScheduleRequest,
    ArticleUpdate,
    TickDueResponse,
)
from app.services.article_generator import ArticleGenerator
from app.services.article_publisher import ArticlePublisher
from app.services.article_service import ArticleService
from app.services.seo_optimizer import SeoOptimizer

router = APIRouter(prefix="/articles", tags=["articles"])


def _response(article: object) -> ArticleResponse:
    return ArticleResponse.model_validate(article)


@router.post("/", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    data: ArticleCreate, db: AsyncSession = Depends(get_db)
) -> ArticleResponse:
    """Create a manual draft."""
    try:
        return _response(await ArticleService(db).create(data))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Article slug already exists") from None


@router.post("/generate", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def generate_article(
    data: ArticleGenerateRequest, db: AsyncSession = Depends(get_db)
) -> ArticleResponse:
    """Generate a grounded draft through the article service."""
    try:
        return _response(await ArticleGenerator(db).generate(data))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Generated article slug already exists") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.get("/", response_model=ArticleListResponse)
async def list_articles(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    company_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> ArticleListResponse:
    """List filtered articles."""
    items, total = await ArticleService(db).list(
        limit=limit, offset=offset, company_id=company_id, status=status_filter
    )
    return ArticleListResponse(
        items=[_response(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/tick-due", response_model=TickDueResponse)
async def tick_due_articles(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> TickDueResponse:
    """Publish due scheduled articles after admin-token authorization."""
    allowed = (settings.graph_sync_token and x_admin_token == settings.graph_sync_token) or (
        settings.debug and not settings.graph_sync_token
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="admin token required")
    processed, published, failed = await ArticlePublisher(db, settings).tick_due()
    return TickDueResponse(processed=processed, published=published, failed=failed)


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: UUID, db: AsyncSession = Depends(get_db)
) -> ArticleResponse:
    """Get one article."""
    article = await ArticleService(db).get(article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return _response(article)


@router.patch("/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: UUID, data: ArticleUpdate, db: AsyncSession = Depends(get_db)
) -> ArticleResponse:
    """Edit operator-controlled fields."""
    article = await ArticleService(db).update(article_id, data)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return _response(article)


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(article_id: UUID, db: AsyncSession = Depends(get_db)) -> Response:
    """Delete one article."""
    if not await ArticleService(db).delete(article_id):
        raise HTTPException(status_code=404, detail="Article not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{article_id}/schedule", response_model=ArticleResponse)
async def schedule_article(
    article_id: UUID,
    data: ArticleScheduleRequest,
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    """Schedule an article for the due queue."""
    try:
        return _response(await ArticlePublisher(db).schedule(article_id, data.scheduled_at))
    except LookupError:
        raise HTTPException(status_code=404, detail="Article not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.post("/{article_id}/publish", response_model=ArticleResponse)
async def publish_article(
    article_id: UUID, db: AsyncSession = Depends(get_db)
) -> ArticleResponse:
    """Publish immediately through the configured article channel."""
    try:
        return _response(await ArticlePublisher(db).publish(article_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="Article not found") from None
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None


@router.post("/{article_id}/optimize", response_model=ArticleResponse)
async def optimize_article(
    article_id: UUID,
    use_llm: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    """Populate SEO metadata, keywords, and controlled internal links."""
    article = await ArticleService(db).get(article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return _response(await SeoOptimizer(db).optimize(article, use_llm=use_llm))
