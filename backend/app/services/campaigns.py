"""Создание кампании в Keitaro вместе с её потоками.

Кампания получает два потока, которые проверяются по порядку:
1. перехватывающий: трафик не из нужной страны уходит на запасной сайт;
2. обычный: остальной трафик (нужная страна) идёт на оффер целиком.
"""
import logging
import secrets
import string

from app.keitaro import KeitaroClient, KeitaroError
from app.services.offers import ensure_offer_exists
from app.services.shares import TOTAL_SHARE
from app.services.streams import EDITABLE_SCHEMA

logger = logging.getLogger(__name__)

ALIAS_LENGTH = 8
ALIAS_ALPHABET = string.ascii_lowercase + string.digits

CAMPAIGN_TYPE = "position"  # потоки проверяются по позиции
FALLBACK_URL = "https://www.google.com"

GEO_STREAM_POSITION = 1
OFFER_STREAM_POSITION = 2

STREAM_TYPE_FORCED = "forced"
STREAM_TYPE_REGULAR = "regular"
REDIRECT_SCHEMA = "redirect"
REDIRECT_ACTION = "http"
# Keitaro требует action_type у любого потока, даже если трафик идёт на офферы.
OFFER_STREAM_ACTION = "http"
COUNTRY_FILTER = "country"
FILTER_MODE_REJECT = "reject"


def generate_alias() -> str:
    return "".join(
        secrets.choice(ALIAS_ALPHABET) for _ in range(ALIAS_LENGTH)
    )


def geo_stream_payload(campaign_id: int, geo: str) -> dict:
    """Поток-фильтр: всё, что не из страны geo, уводим на запасной сайт."""
    return {
        "campaign_id": campaign_id,
        "name": f"Not {geo} -> Google",
        "type": STREAM_TYPE_FORCED,
        "position": GEO_STREAM_POSITION,
        "schema": REDIRECT_SCHEMA,
        "action_type": REDIRECT_ACTION,
        "action_payload": FALLBACK_URL,
        "filters": [
            {
                "name": COUNTRY_FILTER,
                "mode": FILTER_MODE_REJECT,
                "payload": [geo],
            }
        ],
    }


def offer_stream_payload(campaign_id: int, offer_id: int) -> dict:
    """Поток с одним оффером, который получает весь трафик потока."""
    return {
        "campaign_id": campaign_id,
        "name": f"Offer {offer_id}",
        "type": STREAM_TYPE_REGULAR,
        "position": OFFER_STREAM_POSITION,
        "schema": EDITABLE_SCHEMA,
        "action_type": OFFER_STREAM_ACTION,
        "offers": [{"offer_id": offer_id, "share": TOTAL_SHARE}],
    }


def _delete_quietly(client: KeitaroClient, campaign_id: int) -> None:
    """Откат: удалить недособранную кампанию, не заслоняя исходную ошибку."""
    try:
        client.delete_campaign(campaign_id)
    except KeitaroError:
        logger.exception("Не удалось удалить кампанию %s", campaign_id)


def create_campaign_with_streams(
    client: KeitaroClient,
    name: str,
    geo: str,
    offer_id: int,
    *,
    domain_id: int,
    group_id: int,
    traffic_source_id: int,
) -> dict:
    """Создаёт кампанию с потоками и возвращает её так, как ответил Keitaro.

    Если оффера нет, ничего не создаётся (OfferNotFoundError).
    Если Keitaro не принял поток, кампания удаляется и ошибка
    пробрасывается дальше (KeitaroError).
    """
    ensure_offer_exists(client, offer_id)
    campaign = client.create_campaign({
        "name": name,
        "alias": generate_alias(),
        "type": CAMPAIGN_TYPE,
        "domain_id": domain_id,
        "group_id": group_id,
        "traffic_source_id": traffic_source_id,
    })
    campaign_id = campaign["id"]
    try:
        client.create_stream(geo_stream_payload(campaign_id, geo))
        client.create_stream(offer_stream_payload(campaign_id, offer_id))
    except KeitaroError:
        _delete_quietly(client, campaign_id)
        raise
    return campaign
