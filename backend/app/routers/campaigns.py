from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_client, keitaro_unavailable
from app.keitaro import KeitaroClient, KeitaroError
from app.schemas import (
    CampaignCreate,
    CampaignRead,
    CampaignSearchRead,
    CampaignStreamsRead,
)
from app.services.campaign_search import search_campaigns
from app.services.campaigns import create_campaign_with_streams
from app.services.offers import (
    DEFAULT_SEARCH_LIMIT,
    MAX_SEARCH_LIMIT,
    OfferNotFoundError,
)
from app.services.workspace import load_workspace

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignSearchRead])
def find_campaigns(
    q: str = "",
    limit: int = Query(DEFAULT_SEARCH_LIMIT, ge=1, le=MAX_SEARCH_LIMIT),
    client: KeitaroClient = Depends(get_client),
) -> list[dict]:
    try:
        campaigns = client.list_campaigns()
    except KeitaroError as error:
        raise keitaro_unavailable(error) from error
    return search_campaigns(campaigns, q, limit)


@router.post(
    "", response_model=CampaignRead, status_code=HTTPStatus.CREATED
)
def create_campaign(
    data: CampaignCreate,
    client: KeitaroClient = Depends(get_client),
) -> dict:
    try:
        return create_campaign_with_streams(
            client,
            data.name,
            data.geo,
            data.offer_id,
            domain_id=settings.keitaro_domain_id,
            group_id=settings.keitaro_group_id,
            traffic_source_id=settings.keitaro_traffic_source_id,
        )
    except OfferNotFoundError as error:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    except KeitaroError as error:
        raise keitaro_unavailable(error) from error


def _workspace(
    campaign_id: int,
    client: KeitaroClient,
    db: Session,
    *,
    refresh: bool,
) -> dict:
    try:
        streams = load_workspace(client, db, campaign_id, refresh=refresh)
    except KeitaroError as error:
        if error.status_code == HTTPStatus.NOT_FOUND:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Кампания {campaign_id} не найдена",
            ) from error
        raise keitaro_unavailable(error) from error
    return {
        "campaign_id": campaign_id,
        "keitaro_url": settings.campaign_admin_url(campaign_id),
        "streams": streams,
    }


@router.get("/{campaign_id}/streams", response_model=CampaignStreamsRead)
def get_campaign_streams(
    campaign_id: int,
    client: KeitaroClient = Depends(get_client),
    db: Session = Depends(get_db),
) -> dict:
    return _workspace(campaign_id, client, db, refresh=False)


@router.post(
    "/{campaign_id}/streams/refresh", response_model=CampaignStreamsRead
)
def refresh_campaign_streams(
    campaign_id: int,
    client: KeitaroClient = Depends(get_client),
    db: Session = Depends(get_db),
) -> dict:
    return _workspace(campaign_id, client, db, refresh=True)
