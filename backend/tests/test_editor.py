import random

import pytest

from app.services.editor import (
    EditorError,
    add_offer,
    remove_offer,
    restore_offer,
    toggle_pin,
)
from app.services.shares import OfferShare, recalculate_shares


def shares(offers):
    return [o.share for o in offers]


def three():
    return recalculate_shares([OfferShare(1), OfferShare(2), OfferShare(3)])


def test_add_to_empty_gets_100():
    assert shares(add_offer([], 7)) == [100]


def test_add_to_three_makes_25_each():
    assert shares(add_offer(three(), 4)) == [25, 25, 25, 25]


def test_add_duplicate_is_error():
    with pytest.raises(EditorError):
        add_offer(three(), 2)


def test_add_removed_offer_brings_it_back():
    offers = remove_offer(three(), 2)
    assert shares(add_offer(offers, 2)) == [34, 33, 33]


def test_remove_one_of_three_gives_50_50():
    result = remove_offer(three(), 3)
    assert shares(result) == [50, 50, 0]
    assert result[2].removed


def test_remove_and_bring_back_round_trip():
    start = three()
    assert restore_offer(remove_offer(start, 2), 2) == start


def test_remove_unknown_or_already_removed_is_error():
    with pytest.raises(EditorError):
        remove_offer(three(), 99)
    with pytest.raises(EditorError):
        remove_offer(remove_offer(three(), 1), 1)


def test_restore_not_removed_is_error():
    with pytest.raises(EditorError):
        restore_offer(three(), 1)


def test_removing_pinned_offer_clears_pin():
    offers = toggle_pin(three(), 1)
    result = remove_offer(offers, 1)
    assert not result[0].pinned and result[0].removed


def test_pin_keeps_share_when_another_is_added():
    offers = toggle_pin(add_offer([], 1), 1)
    assert offers[0].pinned and offers[0].share == 100
    # закреплённый оффер на 100 не оставляет места новому:
    # закрепление снимается
    result = add_offer(offers, 2)
    assert shares(result) == [50, 50] and not result[0].pinned


def test_pin_holds_while_others_change():
    offers = recalculate_shares([OfferShare(i) for i in range(1, 5)])  # 25 x4
    offers = toggle_pin(offers, 1)
    offers = remove_offer(offers, 4)
    assert shares(offers) == [25, 38, 37, 0] and offers[0].pinned


def test_pinning_everything_then_removing_releases_pins():
    offers = recalculate_shares([OfferShare(i) for i in range(1, 5)])
    for offer_id in (1, 2, 3):
        offers = toggle_pin(offers, offer_id)
    result = remove_offer(offers, 4)
    assert shares(result[:3]) == [34, 33, 33]
    assert not any(o.pinned for o in result)


def test_toggle_pin_twice_unpins():
    offers = toggle_pin(toggle_pin(three(), 1), 1)
    assert not offers[0].pinned


def test_pin_removed_or_unknown_is_error():
    with pytest.raises(EditorError):
        toggle_pin(remove_offer(three(), 1), 1)
    with pytest.raises(EditorError):
        toggle_pin(three(), 99)


def state(offers):
    return [(o.offer_id, o.share, o.pinned, o.removed) for o in offers]


def test_operations_do_not_mutate_input():
    start = three()
    snapshot = state(start)
    add_offer(start, 9)
    remove_offer(start, 1)
    toggle_pin(start, 2)
    assert snapshot == state(start)


ACTIONS = {
    "add": add_offer,
    "remove": remove_offer,
    "restore": restore_offer,
    "pin": toggle_pin,
}


def test_random_operations_always_sum_to_100():
    rng = random.Random(3)
    offers, performed = [], 0
    for _ in range(3000):
        ids = [o.offer_id for o in offers]
        action = rng.choice(list(ACTIONS))
        if ids and action != "add":
            offer_id = rng.choice(ids)
        else:
            offer_id = rng.randint(1, 12)
        func = ACTIONS[action]
        try:
            offers = func(offers, offer_id)
        except EditorError:
            continue
        performed += 1
        active = [o for o in offers if not o.removed]
        if active:
            assert sum(o.share for o in active) == 100
        assert all(o.share == 0 for o in offers if o.removed)
        assert len({o.offer_id for o in offers}) == len(offers)
    assert performed > 1000
