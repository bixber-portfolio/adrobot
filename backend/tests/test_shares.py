import random

import pytest

from app.services.shares import OfferShare, ShareError, recalculate_shares


def shares(offers):
    return [o.share for o in offers]


def make(count, **kwargs):
    return [OfferShare(offer_id=i, **kwargs) for i in range(1, count + 1)]


def test_four_offers_get_25_each():
    assert shares(recalculate_shares(make(4))) == [25, 25, 25, 25]


def test_three_offers_remainder_goes_to_first():
    assert shares(recalculate_shares(make(3))) == [34, 33, 33]


def test_removed_offer_gets_zero_and_others_share_100():
    offers = make(4)
    offers[1].removed = True
    assert shares(recalculate_shares(offers)) == [34, 0, 33, 33]


def test_pinned_share_is_kept_and_rest_is_split():
    offers = make(3)
    offers[0].pinned, offers[0].share = True, 50
    result = recalculate_shares(offers)
    assert shares(result) == [50, 25, 25]
    assert result[0].pinned


def test_pinned_with_odd_remainder():
    offers = make(3)
    offers[0].pinned, offers[0].share = True, 41
    assert shares(recalculate_shares(offers)) == [41, 30, 29]


def test_all_pinned_summing_to_100_is_kept():
    result = recalculate_shares(
        [OfferShare(1, 30, True), OfferShare(2, 70, True)]
    )
    assert shares(result) == [30, 70] and all(o.pinned for o in result)


def test_all_pinned_not_summing_to_100_releases_pins():
    result = recalculate_shares([
        OfferShare(1, 25, True),
        OfferShare(2, 25, True),
        OfferShare(3, 25, True),
    ])
    assert shares(result) == [34, 33, 33]
    assert not any(o.pinned for o in result)


def test_pins_released_when_free_offer_would_get_zero():
    result = recalculate_shares(
        [OfferShare(1, 50, True), OfferShare(2, 50, True), OfferShare(3)]
    )
    assert shares(result) == [34, 33, 33]
    assert not any(o.pinned for o in result)


def test_pinned_over_100_is_error():
    with pytest.raises(ShareError):
        recalculate_shares(make(2, pinned=True, share=60))


def test_pinned_share_out_of_range_is_error():
    with pytest.raises(ShareError):
        recalculate_shares([OfferShare(1, -5, True), OfferShare(2)])


def test_more_than_100_offers_is_error():
    with pytest.raises(ShareError):
        recalculate_shares(make(101))


def test_all_removed_gives_zeros_without_error():
    assert shares(recalculate_shares(make(3, removed=True))) == [0, 0, 0]


def test_empty_list():
    assert recalculate_shares([]) == []


def test_input_is_not_mutated():
    offers = make(3)
    recalculate_shares(offers)
    assert shares(offers) == [0, 0, 0]


def test_random_cases_keep_invariants():
    rng = random.Random(1)
    checked = 0
    for _ in range(3000):
        offers = [
            OfferShare(
                offer_id=i,
                share=rng.randint(0, 40),
                pinned=rng.random() < 0.3,
                removed=rng.random() < 0.25,
            )
            for i in range(rng.randint(0, 8))
        ]
        try:
            result = recalculate_shares(offers)
        except ShareError:
            continue
        checked += 1
        active = [r for r in result if not r.removed]
        if active:
            assert sum(r.share for r in active) == 100
        assert all(r.share == 0 for r in result if r.removed)
        for before, after in zip(offers, result):
            if after.pinned and not after.removed:
                assert before.pinned and after.share == before.share
        free = [r.share for r in result if not r.removed and not r.pinned]
        if free:
            assert max(free) - min(free) <= 1 and min(free) >= 1
    assert checked > 1500
