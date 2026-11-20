from app.services.editor import EditorError
from app.services.offers import ACTIVE_STATE
from app.services.shares import OfferShare
from app.services.snapshots import PublishedOffer, is_dirty

# Править в редакторе можно потоки с офферами и пустые потоки.
# Остальные (например, редиректы на сайт) показываем, но не меняем.
EDITABLE_SCHEMA = "landings"
DEFAULT_STREAM_POSITION = 0

REPORT_INTERVAL = "today"
REPORT_DIMENSION = "stream_id"
REPORT_MEASURE = "clicks"

StreamState = tuple[list[OfferShare], list[PublishedOffer]]


def is_empty(stream: dict) -> bool:
    """Пустой поток: ни офферов, ни адреса, куда он ведёт."""
    return not stream.get("offers") and not stream.get("action_payload")


def is_editable(stream: dict) -> bool:
    return stream.get("schema") == EDITABLE_SCHEMA or is_empty(stream)


def offers_from_stream(stream: dict) -> list[OfferShare]:
    """Офферы потока в том виде, как их видит редактор.

    Неактивные считаем удалёнными.
    """
    offers = []
    for item in stream.get("offers", []):
        removed = item.get("state") != ACTIVE_STATE
        offers.append(OfferShare(
            offer_id=item["offer_id"],
            share=0 if removed else item["share"],
            removed=removed,
        ))
    return offers


def offers_payload(working: list[OfferShare]) -> list[dict]:
    """Офферы потока в формате Keitaro.

    Удалённые не отправляем: в Keitaro их просто не будет.
    """
    active = [o for o in working if not o.removed]
    if not active:
        raise EditorError("Нельзя отправить поток без активных офферов")
    return [
        {"offer_id": o.offer_id, "share": o.share, "state": ACTIVE_STATE}
        for o in active
    ]


def offers_view(
    working: list[OfferShare], offer_names: dict[int, str]
) -> list[dict]:
    return [
        {
            "offer_id": offer.offer_id,
            "name": offer_names.get(offer.offer_id),
            "share": offer.share,
            "pinned": offer.pinned,
            "removed": offer.removed,
        }
        for offer in working
    ]


def clicks_report_payload(campaign_id: int) -> dict:
    return {
        "range": {"interval": REPORT_INTERVAL},
        "dimensions": [REPORT_DIMENSION],
        "measures": [REPORT_MEASURE],
        "filters": [
            {
                "name": "campaign_id",
                "operator": "EQUALS",
                "expression": campaign_id,
            }
        ],
    }


def clicks_by_stream(report: dict | None) -> dict[int, int]:
    """Клики по потокам из отчёта. Строки без нужных полей пропускаем."""
    result = {}
    for row in (report or {}).get("rows", []):
        stream_id = row.get(REPORT_DIMENSION)
        clicks = row.get(REPORT_MEASURE)
        if stream_id is not None and clicks is not None:
            result[int(stream_id)] = int(clicks)
    return result


def _stream_position(stream: dict) -> int:
    return stream.get("position", DEFAULT_STREAM_POSITION)


def _view(
    stream: dict,
    state: StreamState | None,
    offer_names: dict[int, str],
    clicks: dict[int, int] | None,
) -> dict:
    working, published = state if state else ([], [])
    return {
        "id": stream["id"],
        "name": stream["name"],
        "position": _stream_position(stream),
        "stream_schema": stream.get("schema") or "",
        "editable": is_editable(stream),
        "clicks_today": (
            None if clicks is None else clicks.get(stream["id"], 0)
        ),
        "dirty": is_dirty(working, published),
        "offers": offers_view(working, offer_names),
    }


def build_stream_views(
    streams: list[dict],
    states: dict[int, StreamState],
    offer_names: dict[int, str],
    clicks: dict[int, int] | None,
) -> list[dict]:
    """Данные для экрана редактора: все потоки кампании по порядку.

    Состояние (офферы) есть только у редактируемых потоков.
    clicks=None значит, что статистика недоступна.
    """
    return [
        _view(stream, states.get(stream["id"]), offer_names, clicks)
        for stream in sorted(streams, key=_stream_position)
    ]
