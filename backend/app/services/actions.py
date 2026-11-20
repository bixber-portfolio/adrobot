"""Действия редактора над одним потоком: правки, отмена и отправка."""
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.keitaro import KeitaroClient, KeitaroError
from app.services.drafts import get_campaign_id, load_state, save_state
from app.services.editor import (
    add_offer,
    remove_offer,
    restore_offer,
    toggle_pin,
)
from app.services.offers import ensure_offer_exists
from app.services.shares import OfferShare
from app.services.snapshots import (
    PublishedOffer,
    cancel_changes,
    is_dirty,
    snapshot_of,
)
from app.services.streams import (
    EDITABLE_SCHEMA,
    StreamState,
    offers_payload,
    offers_view,
)

Operation = Callable[[list[OfferShare], int], list[OfferShare]]


class StreamNotOpenedError(Exception):
    """Поток ещё не открывали в редакторе, правок у нас по нему нет."""

    def __init__(self, stream_id: int):
        super().__init__(f"Поток {stream_id} не открыт в редакторе")
        self.stream_id = stream_id


def _load(db: Session, stream_id: int) -> StreamState:
    state = load_state(db, stream_id)
    if state is None:
        raise StreamNotOpenedError(stream_id)
    return state


def _save(
    db: Session,
    stream_id: int,
    working: list[OfferShare],
    published: list[PublishedOffer],
) -> None:
    campaign_id = get_campaign_id(db, stream_id)
    save_state(db, stream_id, campaign_id, working, published)


def _names(client: KeitaroClient) -> dict[int, str]:
    """Названия офферов.

    Не получилось: показываем без названий, правки это не ломает.
    """
    try:
        return {o["id"]: o["name"] for o in client.list_offers()}
    except KeitaroError:
        return {}


def _result(
    client: KeitaroClient,
    stream_id: int,
    working: list[OfferShare],
    published: list[PublishedOffer],
) -> dict:
    return {
        "id": stream_id,
        "dirty": is_dirty(working, published),
        "offers": offers_view(working, _names(client)),
    }


def _apply(
    client: KeitaroClient,
    db: Session,
    stream_id: int,
    state: StreamState,
    working: list[OfferShare],
) -> dict:
    """Сохраняет новый рабочий список и возвращает поток для экрана."""
    published = state[1]
    _save(db, stream_id, working, published)
    return _result(client, stream_id, working, published)


def _edit(
    client: KeitaroClient,
    db: Session,
    stream_id: int,
    operation: Operation,
    offer_id: int,
) -> dict:
    state = _load(db, stream_id)
    return _apply(client, db, stream_id, state, operation(state[0], offer_id))


def add(
    client: KeitaroClient, db: Session, stream_id: int, offer_id: int
) -> dict:
    # Сначала убеждаемся, что поток открыт, и только потом ходим в Keitaro.
    state = _load(db, stream_id)
    ensure_offer_exists(client, offer_id)
    working = add_offer(state[0], offer_id)
    return _apply(client, db, stream_id, state, working)


def remove(
    client: KeitaroClient, db: Session, stream_id: int, offer_id: int
) -> dict:
    return _edit(client, db, stream_id, remove_offer, offer_id)


def restore(
    client: KeitaroClient, db: Session, stream_id: int, offer_id: int
) -> dict:
    return _edit(client, db, stream_id, restore_offer, offer_id)


def pin(
    client: KeitaroClient, db: Session, stream_id: int, offer_id: int
) -> dict:
    return _edit(client, db, stream_id, toggle_pin, offer_id)


def cancel(client: KeitaroClient, db: Session, stream_id: int) -> dict:
    state = _load(db, stream_id)
    working = cancel_changes(*state)
    return _apply(client, db, stream_id, state, working)


def push(client: KeitaroClient, db: Session, stream_id: int) -> dict:
    """Отправить рабочие офферы в Keitaro.

    Если Keitaro не принял, у нас ничего не меняется.
    """
    working, published = _load(db, stream_id)
    if is_dirty(working, published):
        # schema нужна пустому потоку: после отправки он станет офферным.
        payload = {
            "schema": EDITABLE_SCHEMA,
            "offers": offers_payload(working),
        }
        client.update_stream(stream_id, payload)
        published = snapshot_of(working)
        _save(db, stream_id, working, published)
    return _result(client, stream_id, working, published)
