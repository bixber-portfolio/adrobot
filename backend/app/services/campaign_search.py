from app.services.offers import DEFAULT_SEARCH_LIMIT

ARCHIVED_STATE = "deleted"
DEFAULT_STATE = "active"


def _matches(campaign: dict, query: str) -> bool:
    return not query or any(
        query in text
        for text in (
            str(campaign["id"]),
            (campaign.get("name") or "").lower(),
            (campaign.get("alias") or "").lower(),
        )
    )


def search_campaigns(
    campaigns: list[dict],
    query: str = "",
    limit: int | None = DEFAULT_SEARCH_LIMIT,
) -> list[dict]:
    """Кампании (без архивных), у которых номер, название или алиас
    содержат запрос. Сначала новые. limit=None: без ограничения.
    """
    query = query.strip().lower()
    found = [
        {
            "id": campaign["id"],
            "name": campaign.get("name") or "",
            "alias": campaign.get("alias") or "",
            "state": campaign.get("state") or DEFAULT_STATE,
        }
        for campaign in sorted(campaigns, key=lambda c: -c["id"])
        if campaign.get("state") != ARCHIVED_STATE
        and _matches(campaign, query)
    ]
    return found if limit is None else found[:limit]
