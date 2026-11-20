from fastapi import APIRouter, Depends, Query

from app.deps import get_client, keitaro_unavailable
from app.keitaro import KeitaroClient, KeitaroError
from app.schemas import OfferRead
from app.services.offers import (
    DEFAULT_SEARCH_LIMIT,
    MAX_SEARCH_LIMIT,
    search_offers,
)

router = APIRouter(prefix="/api/offers", tags=["offers"])


@router.get("", response_model=list[OfferRead])
def find_offers(
    q: str = "",
    limit: int = Query(DEFAULT_SEARCH_LIMIT, ge=1, le=MAX_SEARCH_LIMIT),
    client: KeitaroClient = Depends(get_client),
) -> list[dict]:
    try:
        offers = client.list_offers()
    except KeitaroError as error:
        raise keitaro_unavailable(error) from error
    return search_offers(offers, q, limit)
