import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import DraftOffer
from app.services.drafts import load_state, save_state
from app.services.shares import OfferShare
from app.services.snapshots import PublishedOffer


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        yield session


def test_unknown_stream_returns_none(db):
    assert load_state(db, 1) is None


def test_roundtrip_keeps_order_flags_and_snapshot(db):
    working = [
        OfferShare(5, 50, True, False),
        OfferShare(3, 50),
        OfferShare(9, 0, False, True),
    ]
    published = [PublishedOffer(5, 60, True), PublishedOffer(9, 0, False)]
    save_state(db, 1, 100, working, published)
    assert load_state(db, 1) == (working, published)


def test_local_only_offer_has_no_snapshot(db):
    save_state(db, 1, 100, [OfferShare(1, 100)], [])
    working, published = load_state(db, 1)
    assert working == [OfferShare(1, 100)] and published == []


def test_save_overwrites_without_leftovers(db):
    save_state(db, 1, 100, [OfferShare(1, 50), OfferShare(2, 50)], [])
    save_state(db, 1, 100, [OfferShare(7, 100)], [])
    assert load_state(db, 1)[0] == [OfferShare(7, 100)]
    assert db.scalar(select(func.count()).select_from(DraftOffer)) == 1


def test_streams_are_independent(db):
    save_state(db, 1, 100, [OfferShare(1, 100)], [])
    save_state(db, 2, 100, [OfferShare(2, 100)], [])
    save_state(db, 1, 100, [OfferShare(3, 100)], [])
    assert load_state(db, 2)[0] == [OfferShare(2, 100)]


def test_save_same_offers_again_does_not_break_unique(db):
    save_state(db, 1, 100, [OfferShare(1, 50), OfferShare(2, 50)], [])
    save_state(
        db, 1, 100,
        [OfferShare(1, 30), OfferShare(2, 70)],
        [PublishedOffer(1, 50, True)],
    )
    working, published = load_state(db, 1)
    assert [(o.offer_id, o.share) for o in working] == [(1, 30), (2, 70)]
    assert published == [PublishedOffer(1, 50, True)]
