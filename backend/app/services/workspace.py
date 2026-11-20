from sqlalchemy.orm import Session

from app.keitaro import KeitaroClient, KeitaroError
from app.services.drafts import load_state, save_state
from app.services.snapshots import merge_keitaro
from app.services.streams import (
    StreamState,
    build_stream_views,
    clicks_by_stream,
    clicks_report_payload,
    is_editable,
    offers_from_stream,
)


def pull_stream(db: Session, campaign_id: int, stream: dict) -> StreamState:
    """Подтянуть один поток из Keitaro в нашу базу.

    Правки «жёлтого» потока сохраняются.
    """
    state = load_state(db, stream["id"])
    working, published = state if state else (None, [])
    working, published = merge_keitaro(
        working, published, offers_from_stream(stream)
    )
    save_state(db, stream["id"], campaign_id, working, published)
    return working, published


def _load_clicks(
    client: KeitaroClient, campaign_id: int
) -> dict[int, int] | None:
    """Клики за сегодня; None, если статистика недоступна.

    Без статистики редактор работать может, ошибкой страницу не ломаем.
    """
    try:
        report = client.build_report(clicks_report_payload(campaign_id))
    except KeitaroError:
        return None
    return clicks_by_stream(report)


def load_workspace(
    client: KeitaroClient,
    db: Session,
    campaign_id: int,
    *,
    refresh: bool = False,
) -> list[dict]:
    """Экран редактора.

    Поток, которого у нас ещё нет, подтягивается из Keitaro сам.
    refresh=True подтягивает из Keitaro все потоки
    (кнопка «Fetch streams from KT»).
    """
    streams = client.get_campaign_streams(campaign_id)
    states = {}
    for stream in filter(is_editable, streams):
        state = None if refresh else load_state(db, stream["id"])
        states[stream["id"]] = state or pull_stream(db, campaign_id, stream)

    offer_names = {o["id"]: o["name"] for o in client.list_offers()}
    clicks = _load_clicks(client, campaign_id)
    return build_stream_views(streams, states, offer_names, clicks)
