"""Push a person into mock/Bitrix24/retailCRM. Default mock, no secrets in git."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_settings
from app.core.config import Settings
from app.schemas.crm import CrmSyncEventResponse, CrmSyncResponse
from app.services.crm import CrmService
from app.services.exceptions import NotFoundError

router = APIRouter(prefix="/crm", tags=["crm"])


def _require_crm_token(settings: Settings, x_admin_token: str | None) -> None:
    if not settings.crm.require_token:
        return
    token = settings.graph_sync_token
    allowed = (token and x_admin_token == token) or (settings.debug and not token)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin token required")


@router.post("/sync/{person_id}", response_model=CrmSyncResponse)
async def sync_person(
    person_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> CrmSyncResponse:
    _require_crm_token(settings, x_admin_token)
    if not settings.crm.enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="CRM disabled")
    try:
        event = await CrmService(db, settings).sync_person(person_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from None
    body = CrmSyncResponse(
        event_id=event.id,
        provider=event.provider,
        status=event.status,
        remote_id=event.remote_id,
    )
    if event.status != "ok":
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=body.model_dump(mode="json"))
    return body


@router.get("/events", response_model=list[CrmSyncEventResponse])
async def list_events(
    person_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> list[CrmSyncEventResponse]:
    _require_crm_token(settings, x_admin_token)
    rows = await CrmService(db, settings).list_events(person_id=person_id, limit=limit, offset=offset)
    return [CrmSyncEventResponse.model_validate(row) for row in rows]
