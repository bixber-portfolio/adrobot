from dataclasses import dataclass, replace

from app.services.shares import OfferShare, recalculate_shares


@dataclass(frozen=True)
class PublishedOffer:
    """Оффер в состоянии «как последний раз было в Keitaro»."""

    offer_id: int
    share: int
    active: bool


def snapshot_of(offers: list[OfferShare]) -> list[PublishedOffer]:
    """Снимок списка: удалённые попадают в него неактивными с долей 0."""
    return [
        PublishedOffer(o.offer_id, 0 if o.removed else o.share, not o.removed)
        for o in offers
    ]


def _matches(offer: OfferShare, published: PublishedOffer | None) -> bool:
    if published is None:  # в Keitaro такого оффера не было
        # Добавили и сразу убрали: от Keitaro ничем не отличается.
        return offer.removed
    if offer.removed:
        return not published.active
    return published.active and offer.share == published.share


def is_dirty(
    working: list[OfferShare], published: list[PublishedOffer]
) -> bool:
    """«Жёлтый» поток: рабочий список отличается от опубликованного.

    Флаг вычисляется на лету, хранить его не нужно.
    """
    by_id = {p.offer_id: p for p in published}
    return any(not _matches(o, by_id.get(o.offer_id)) for o in working)


def cancel_changes(
    working: list[OfferShare], published: list[PublishedOffer]
) -> list[OfferShare]:
    """Откат к опубликованному.

    Офферы, которых в Keitaro не было, исчезают, закрепления снимаются.
    """
    by_id = {p.offer_id: p for p in published}
    result = []
    for offer in working:
        snapshot = by_id.get(offer.offer_id)
        if snapshot is not None:
            result.append(OfferShare(
                snapshot.offer_id,
                snapshot.share,
                pinned=False,
                removed=not snapshot.active,
            ))
    return result


def _disabled_in_keitaro(
    before: PublishedOffer | None, after: OfferShare | None
) -> bool:
    """Был активен в Keitaro, а теперь пропал оттуда или отключён."""
    return (
        before is not None
        and before.active
        and (after is None or after.removed)
    )


def _enabled_in_keitaro(
    before: PublishedOffer | None, after: OfferShare | None
) -> bool:
    """Был отключён в Keitaro, а теперь снова активен."""
    return (
        before is not None
        and not before.active
        and after is not None
        and not after.removed
    )


def _merge_dirty(
    working: list[OfferShare],
    published: list[PublishedOffer],
    keitaro: list[OfferShare],
) -> list[OfferShare]:
    """Правки «жёлтого» потока плюс то, что изменилось в Keitaro."""
    old = {p.offer_id: p for p in published}
    now = {o.offer_id: o for o in keitaro}
    merged, changed = [], False
    for offer in working:
        before, after = old.get(offer.offer_id), now.get(offer.offer_id)
        if not offer.removed and _disabled_in_keitaro(before, after):
            offer, changed = replace(offer, removed=True, pinned=False), True
        elif offer.removed and _enabled_in_keitaro(before, after):
            offer, changed = replace(offer, removed=False), True
        merged.append(offer)

    known = {o.offer_id for o in working}
    for offer in keitaro:
        if offer.offer_id not in known:
            merged.append(OfferShare(offer.offer_id, removed=offer.removed))
            changed = changed or not offer.removed
    return recalculate_shares(merged) if changed else merged


def merge_keitaro(
    working: list[OfferShare] | None,
    published: list[PublishedOffer],
    keitaro: list[OfferShare],
) -> tuple[list[OfferShare], list[PublishedOffer]]:
    """Подтянуть поток из Keitaro. Возвращает (рабочий список, снимок).

    Снимок всегда становится равным Keitaro. Чистый поток целиком берётся
    из Keitaro. У «жёлтого» потока правки сохраняются, поверх накладывается
    то, что изменилось в Keitaro.
    """
    in_keitaro = {o.offer_id for o in keitaro}
    # Оффер был в Keitaro, а теперь пропал: храним как удалённый,
    # его можно вернуть.
    gone = [
        OfferShare(p.offer_id, removed=True)
        for p in published
        if p.offer_id not in in_keitaro
    ]
    new_published = snapshot_of(keitaro) + snapshot_of(gone)

    if working is None or not is_dirty(working, published):
        pins = {
            o.offer_id for o in working or [] if o.pinned and not o.removed
        }
        fresh = [
            replace(o, pinned=o.offer_id in pins and not o.removed)
            for o in keitaro
        ]
        return fresh + gone, new_published

    return _merge_dirty(working, published, keitaro), new_published
