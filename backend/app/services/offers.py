from app.keitaro import KeitaroClient

DEFAULT_SEARCH_LIMIT = 20
MAX_SEARCH_LIMIT = 500
ACTIVE_STATE = "active"


class OfferNotFoundError(Exception):
    """Оффера с таким номером нет в Keitaro."""

    def __init__(self, offer_id: int):
        super().__init__(f"Оффер {offer_id} не найден в Keitaro")
        self.offer_id = offer_id


def _matches(offer: dict, query: str) -> bool:
    return (
        not query
        or query in str(offer["id"])
        or query in offer["name"].lower()
    )


def search_offers(
    offers: list[dict],
    query: str = "",
    limit: int | None = DEFAULT_SEARCH_LIMIT,
) -> list[dict]:
    """Активные офферы, у которых номер или название содержат запрос.

    Регистр и пробелы по краям запроса не важны. limit=None: без ограничения.
    """
    query = query.strip().lower()
    found = [
        {"id": offer["id"], "name": offer["name"]}
        for offer in offers
        if offer.get("state", ACTIVE_STATE) == ACTIVE_STATE
        and _matches(offer, query)
    ]
    return found if limit is None else found[:limit]


def ensure_offer_exists(client: KeitaroClient, offer_id: int) -> None:
    if not any(offer["id"] == offer_id for offer in client.list_offers()):
        raise OfferNotFoundError(offer_id)
