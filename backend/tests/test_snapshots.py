import pytest

from app.services.editor import (
    add_offer,
    remove_offer,
    restore_offer,
    toggle_pin,
)
from app.services.shares import OfferShare
from app.services.snapshots import (
    PublishedOffer,
    cancel_changes,
    is_dirty,
    merge_keitaro,
    snapshot_of,
)


def kt(*items):
    """Офферы из Keitaro: (id, share) активный или (id, None) отключённый."""
    return [OfferShare(i, s or 0, removed=s is None) for i, s in items]


def opened(*items):
    k = kt(*items)
    return merge_keitaro(None, [], k)  # открыли поток впервые


def shares(offers):
    return {o.offer_id: o.share for o in offers}


def rows(offers):
    return [(o.offer_id, o.share, o.removed) for o in offers]


def test_first_open_is_clean_and_equals_keitaro():
    working, published = opened((1, 50), (2, 50))
    assert shares(working) == {1: 50, 2: 50}
    assert not is_dirty(working, published)


@pytest.mark.parametrize("action", [
    lambda w: add_offer(w, 3),
    lambda w: remove_offer(w, 1),
])
def test_local_edit_makes_dirty(action):
    working, published = opened((1, 50), (2, 50))
    assert is_dirty(action(working), published)


def test_pin_alone_is_not_dirty():
    working, published = opened((1, 50), (2, 50))
    assert not is_dirty(toggle_pin(working, 1), published)


def test_add_then_remove_same_offer_is_clean_again():
    working, published = opened((1, 100))
    working = remove_offer(add_offer(working, 2), 2)
    assert not is_dirty(working, published)


def test_remove_then_restore_is_clean_again():
    working, published = opened((1, 50), (2, 50))
    working = restore_offer(remove_offer(working, 1), 1)
    assert not is_dirty(working, published)


def test_push_snapshot_makes_clean():
    working, published = opened((1, 50), (2, 50))
    working = remove_offer(add_offer(working, 3), 1)
    assert is_dirty(working, published)
    assert not is_dirty(working, snapshot_of(working))


def test_cancel_restores_removed_and_drops_added():
    working, published = opened((1, 50), (2, 50))
    working = remove_offer(add_offer(working, 3), 1)
    back = cancel_changes(working, published)
    assert rows(back) == [(1, 50, False), (2, 50, False)]
    assert not is_dirty(back, published)


def test_cancel_keeps_what_was_pushed():
    working, published = opened((1, 100))
    working = add_offer(working, 2)
    published = snapshot_of(working)  # Push
    working = remove_offer(working, 1)
    back = cancel_changes(working, published)
    assert shares(back) == {1: 50, 2: 50}


def test_cancel_resets_pins_and_ignores_keitaro_changes():
    working, published = opened((1, 50), (2, 50))
    working = toggle_pin(working, 1)
    assert not any(o.pinned for o in cancel_changes(working, published))


def test_cancel_keeps_offer_disabled_in_keitaro_as_removed():
    working, published = opened((1, 100), (2, None))
    back = cancel_changes(restore_offer(working, 2), published)
    assert [(o.offer_id, o.removed) for o in back] == [(1, False), (2, True)]


def test_refresh_clean_stream_takes_keitaro_as_is():
    working, published = opened((1, 50), (2, 50))
    working, published = merge_keitaro(
        working, published, kt((1, 30), (2, 30), (3, 40))
    )
    assert shares(working) == {1: 30, 2: 30, 3: 40}
    assert not is_dirty(working, published)


def test_refresh_clean_stream_marks_deleted_in_keitaro_as_removed():
    working, published = opened((1, 50), (2, 50))
    working, published = merge_keitaro(working, published, kt((1, 100)))
    assert rows(working) == [(1, 100, False), (2, 0, True)]
    assert not is_dirty(working, published)
    # и его можно вернуть
    assert shares(restore_offer(working, 2)) == {1: 50, 2: 50}


def test_refresh_clean_stream_marks_disabled_in_keitaro_as_removed():
    working, published = opened((1, 50), (2, 50))
    working, _ = merge_keitaro(working, published, kt((1, 100), (2, None)))
    assert working[1].removed


def test_refresh_dirty_stream_keeps_local_edits():
    working, published = opened((1, 50), (2, 50))
    working = remove_offer(working, 2)  # локально убрали 2
    new_working, new_published = merge_keitaro(
        working, published, kt((1, 50), (2, 50))
    )
    assert new_working[1].removed
    assert is_dirty(new_working, new_published)


def test_refresh_dirty_stream_adds_new_offer_from_keitaro_and_recalculates():
    working, published = opened((1, 50), (2, 50))
    working = remove_offer(working, 2)
    new_working, new_published = merge_keitaro(
        working, published, kt((1, 50), (2, 50), (3, 0))
    )
    assert shares(new_working) == {1: 50, 2: 0, 3: 50}
    assert sum(o.share for o in new_working) == 100
    assert is_dirty(new_working, new_published)


def test_refresh_dirty_stream_marks_offer_deleted_in_keitaro():
    working, published = opened((1, 50), (2, 50))
    working = add_offer(working, 3)
    new_working, _ = merge_keitaro(working, published, kt((1, 100)))
    by_id = {o.offer_id: o for o in new_working}
    assert by_id[2].removed
    assert not by_id[3].removed  # локальный новый оффер не трогаем
    assert sum(o.share for o in new_working) == 100


def test_refresh_dirty_stream_unremoves_offer_reenabled_in_keitaro():
    working, published = opened((1, 100), (2, None))
    working = add_offer(working, 3)
    new_working, _ = merge_keitaro(working, published, kt((1, 50), (2, 50)))
    assert not {o.offer_id: o for o in new_working}[2].removed


def test_refresh_keeps_local_restore_of_offer_disabled_in_keitaro():
    working, published = opened((1, 100), (2, None))
    working = restore_offer(working, 2)
    new_working, _ = merge_keitaro(working, published, kt((1, 100), (2, None)))
    assert not {o.offer_id: o for o in new_working}[2].removed


def test_refresh_always_sets_snapshot_equal_to_keitaro():
    working, published = opened((1, 50), (2, 50))
    working = add_offer(working, 3)
    _, new_published = merge_keitaro(working, published, kt((1, 70), (2, 30)))
    snapshot = {p.offer_id: (p.share, p.active) for p in new_published}
    assert snapshot == {1: (70, True), 2: (30, True)}


def test_sum_is_100_after_any_merge_when_active_offers_exist():
    working, published = opened((1, 50), (2, 50))
    working = add_offer(working, 3)
    new_working, _ = merge_keitaro(
        working, published, kt((1, 20), (2, 20), (4, 60))
    )
    assert sum(o.share for o in new_working if not o.removed) == 100


P = PublishedOffer
S = OfferShare
ONE_FULL = S(1, 100)
SECOND_REMOVED = S(2, 0, removed=True)


@pytest.mark.parametrize("working, published, dirty", [
    # совпадает
    ([ONE_FULL], [P(1, 100, True)], False),
    # отличается только доля
    ([S(1, 60), S(2, 40)], [P(1, 50, True), P(2, 50, True)], True),
    # отличается только «удалён»: доли чужих не затронуты
    ([ONE_FULL, SECOND_REMOVED], [P(1, 100, True), P(2, 0, True)], True),
    # в Keitaro был отключён, у нас активен
    ([ONE_FULL, S(2, 0)], [P(1, 100, True), P(2, 0, False)], True),
    # нового оффера в Keitaro не было, у нас он активный с долей 0
    ([ONE_FULL, S(2, 0)], [P(1, 100, True)], True),
    # новый, но сразу удалён: от Keitaro не отличается
    ([ONE_FULL, SECOND_REMOVED], [P(1, 100, True)], False),
    # отключён и там, и у нас
    ([ONE_FULL, SECOND_REMOVED], [P(1, 100, True), P(2, 0, False)], False),
])
def test_is_dirty_each_difference_on_its_own(working, published, dirty):
    assert is_dirty(working, published) is dirty
