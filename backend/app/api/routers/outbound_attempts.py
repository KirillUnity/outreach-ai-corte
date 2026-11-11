"""Read-only list of outbound vendor attempts."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.outbound_attempt import OutboundAttemptResponse
from app.services.outbound_attempts import list_attempts

router = APIRouter(tags=["outbound-attempts"])


@router.get(
    "/outbound-attempts",
    response_model=list[OutboundAttemptResponse],
    summary="List outbound attempts",
)
async def list_outbound_attempts(
    db: AsyncSession = Depends(get_db),
) -> list[OutboundAttemptResponse]:
    """Show attempt count, last error, next try time, status, and target."""
    rows = await list_attempts(db)
    return [OutboundAttemptResponse.model_validate(row) for row in rows]
