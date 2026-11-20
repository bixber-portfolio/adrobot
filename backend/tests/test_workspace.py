from http import HTTPStatus

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.keitaro import KeitaroError
from app.services.drafts import load_state, save_state
from app.services.editor import add_offer, remove_offer
from app.services.workspace import load_workspace


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        yield session


CAMPAIGN_ID = 7
STREAM_ID = 11


def stream(offers, schema="landings"):
    return {
        "id": STREAM_ID,
        "name": "S",
        "position": 1,
        "schema": schema,
        "offers": [
            {"offer_id": i, "share": s, "state": st} for i, s, st in offers
        ],
    }


class Fake:
    def __init__(self, offers, report=None, report_error=None):
        self.offers = offers
        self.report = report
        self.report_error = report_error
        self.stream_calls = 0

    def get_campaign_streams(self, campaign_id):
        self.stream_calls += 1
        return [stream(self.offers)]

    def list_offers(self):
        return [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]

    def build_report(self, payload):
        if self.report_error:
            raise self.report_error
        return self.report or {"rows": []}


A50 = [(1, 50, "active"), (2, 50, "active")]


def offers_of(views):
    return {
        o["offer_id"]: (o["share"], o["removed"]) for o in views[0]["offers"]
    }


def test_first_open_pulls_from_keitaro_and_saves(db):
    views = load_workspace(Fake(A50), db, CAMPAIGN_ID)
    assert views[0]["dirty"] is False
    assert offers_of(views) == {1: (50, False), 2: (50, False)}
    assert load_state(db, STREAM_ID) is not None


def test_second_open_uses_saved_state_not_keitaro(db):
    load_workspace(Fake(A50), db, CAMPAIGN_ID)
    working, published = load_state(db, STREAM_ID)
    # локальная правка
    save_state(db, STREAM_ID, CAMPAIGN_ID, remove_offer(working, 2), published)
    changed_in_keitaro = Fake([(1, 10, "active"), (2, 90, "active")])
    views = load_workspace(changed_in_keitaro, db, CAMPAIGN_ID)
    assert views[0]["dirty"] is True
    assert offers_of(views) == {1: (100, False), 2: (0, True)}


def test_refresh_clean_stream_takes_keitaro(db):
    load_workspace(Fake(A50), db, CAMPAIGN_ID)
    changed = Fake([(1, 30, "active"), (2, 70, "active")])
    views = load_workspace(changed, db, CAMPAIGN_ID, refresh=True)
    assert views[0]["dirty"] is False
    assert offers_of(views) == {1: (30, False), 2: (70, False)}


def test_refresh_dirty_stream_keeps_local_edits_and_adds_new(db):
    load_workspace(Fake(A50), db, CAMPAIGN_ID)
    working, published = load_state(db, STREAM_ID)
    save_state(db, STREAM_ID, CAMPAIGN_ID, remove_offer(working, 2), published)
    fake = Fake(A50 + [(3, 0, "active")])
    views = load_workspace(fake, db, CAMPAIGN_ID, refresh=True)
    assert views[0]["dirty"] is True
    assert offers_of(views) == {1: (50, False), 2: (0, True), 3: (50, False)}


def test_refresh_marks_offer_deleted_in_keitaro_as_restorable(db):
    load_workspace(Fake(A50), db, CAMPAIGN_ID)
    fake = Fake([(1, 100, "active")])
    views = load_workspace(fake, db, CAMPAIGN_ID, refresh=True)
    assert offers_of(views) == {1: (100, False), 2: (0, True)}
    assert views[0]["dirty"] is False


def test_not_editable_streams_are_shown_but_not_saved(db):
    class OnlyRedirect(Fake):
        def get_campaign_streams(self, campaign_id):
            return [{**stream([], schema="redirect"),
                     "action_payload": "https://www.google.com"}]

    views = load_workspace(OnlyRedirect([]), db, CAMPAIGN_ID)
    assert [(v["id"], v["editable"]) for v in views] == [(STREAM_ID, False)]
    assert load_state(db, STREAM_ID) is None


def test_empty_stream_of_other_schema_is_opened_for_editing(db):
    class EmptyRedirect(Fake):
        def get_campaign_streams(self, campaign_id):
            return [{**stream([], schema="redirect"), "action_payload": ""}]

    views = load_workspace(EmptyRedirect([]), db, CAMPAIGN_ID)
    assert [(v["id"], v["editable"]) for v in views] == [(STREAM_ID, True)]
    assert load_state(db, STREAM_ID) is not None


def test_stream_added_in_keitaro_appears_on_next_open_without_fetch(db):
    class WithNewStream(Fake):
        def get_campaign_streams(self, campaign_id):
            new = {**stream([(3, 100, "active")]), "id": 12, "name": "New"}
            return [stream(self.offers), new]

    load_workspace(Fake(A50), db, CAMPAIGN_ID)
    working, published = load_state(db, STREAM_ID)
    save_state(
        db, STREAM_ID, CAMPAIGN_ID, remove_offer(working, 2), published
    )
    views = load_workspace(WithNewStream(A50), db, CAMPAIGN_ID)
    assert [v["id"] for v in views] == [STREAM_ID, 12]
    assert views[0]["dirty"] is True  # локальные правки старого потока целы
    assert views[1]["dirty"] is False
    assert {o["offer_id"] for o in views[1]["offers"]} == {3}


def test_report_failure_gives_none_clicks_but_state_is_saved(db):
    error = KeitaroError(HTTPStatus.FORBIDDEN, "no")
    views = load_workspace(Fake(A50, report_error=error), db, CAMPAIGN_ID)
    assert views[0]["clicks_today"] is None
    assert load_state(db, STREAM_ID) is not None


def test_keitaro_failure_propagates_and_saves_nothing(db):
    class Broken(Fake):
        def get_campaign_streams(self, campaign_id):
            raise KeitaroError(HTTPStatus.INTERNAL_SERVER_ERROR, "boom")

    with pytest.raises(KeitaroError):
        load_workspace(Broken([]), db, CAMPAIGN_ID)
    assert load_state(db, STREAM_ID) is None


def test_added_locally_survives_second_open(db):
    load_workspace(Fake(A50), db, CAMPAIGN_ID)
    working, published = load_state(db, STREAM_ID)
    save_state(db, STREAM_ID, CAMPAIGN_ID, add_offer(working, 3), published)
    views = load_workspace(Fake(A50), db, CAMPAIGN_ID)
    assert set(offers_of(views)) == {1, 2, 3} and views[0]["dirty"] is True


def test_open_does_not_pull_by_itself_when_state_exists(db):
    load_workspace(Fake(A50), db, CAMPAIGN_ID)
    changed = Fake([(1, 10, "active"), (2, 90, "active")])
    views = load_workspace(changed, db, CAMPAIGN_ID)
    # Keitaro изменился, но мы не тянули
    assert offers_of(views) == {1: (50, False), 2: (50, False)}
