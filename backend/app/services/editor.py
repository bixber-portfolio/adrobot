from dataclasses import replace

from app.services.shares import OfferShare, recalculate_shares


class EditorError(ValueError):
    """Действие в редакторе невозможно (оффера нет, он уже есть и т. п.)."""


def _find(offers: list[OfferShare], offer_id: int) -> int | None:
    for index, offer in enumerate(offers):
        if offer.offer_id == offer_id:
            return index
    return None


def _locate(
    offers: list[OfferShare],
    offer_id: int,
    *,
    removed: bool,
    error: str,
) -> int:
    """Индекс оффера, который есть в списке и в нужном состоянии.

    removed задаёт нужное состояние: удалён оффер или нет.
    """
    index = _find(offers, offer_id)
    if index is None or offers[index].removed != removed:
        raise EditorError(error.format(offer_id))
    return index


def _update(
    offers: list[OfferShare], index: int, **changes: object
) -> list[OfferShare]:
    """Копия списка с изменённым оффером; доли пересчитываются."""
    updated = list(offers)
    updated[index] = replace(offers[index], **changes)
    return recalculate_shares(updated)


def add_offer(offers: list[OfferShare], offer_id: int) -> list[OfferShare]:
    index = _find(offers, offer_id)
    if index is None:
        return recalculate_shares([*offers, OfferShare(offer_id)])
    if offers[index].removed:
        return restore_offer(offers, offer_id)
    raise EditorError(f"Оффер {offer_id} уже есть в потоке")


def remove_offer(
    offers: list[OfferShare], offer_id: int
) -> list[OfferShare]:
    index = _locate(
        offers,
        offer_id,
        removed=False,
        error="Оффера {} нет в потоке или он уже удалён",
    )
    return _update(offers, index, removed=True, pinned=False)


def restore_offer(
    offers: list[OfferShare], offer_id: int
) -> list[OfferShare]:
    index = _locate(
        offers,
        offer_id,
        removed=True,
        error="Оффер {} не удалён, возвращать нечего",
    )
    return _update(offers, index, removed=False, pinned=False)


def toggle_pin(offers: list[OfferShare], offer_id: int) -> list[OfferShare]:
    index = _locate(
        offers,
        offer_id,
        removed=False,
        error="Оффера {} нет в потоке или он удалён",
    )
    return _update(offers, index, pinned=not offers[index].pinned)
