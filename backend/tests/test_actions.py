from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.deps import get_client
from app.keitaro import KeitaroError
from app.main import app
from app.services import actions
from app.services.actions import StreamNotOpenedError
from app.services.drafts import load_state
from app.services.editor import EditorError
from app.services.offers import OfferNotFoundError
from app.services.shares import OfferShare
from app.services.snapshots import is_dirty
from app.services.streams import offers_payload
from app.services.workspace import load_workspace

STREAM = {
    "id": 11,
    "name": "S",
    "position": 1,
    "schema": "landings",
    "offers": [
        {"offer_id": 1, "share": 50, "state": "active"},
        {"offer_id": 2, "share": 50, "state": "active"},
    ],
}
OFFER_IDS = (1, 2, 3, 4)


class Fake:
    def __init__(self, push_error=None, offers_error=None):
        self.push_error = push_error
        self.offers_error = offers_error
        self.updates = []

    def get_campaign_streams(self, campaign_id):
        return [STREAM]

    def list_offers(self):
        if self.offers_error:
            raise self.offers_error
        return [
            {"id": i, "name": f"Offer {i}", "state": "active"}
            for i in OFFER_IDS
        ]

    def build_report(self, payload):
        return {"rows": []}

    def update_stream(self, stream_id, payload):
        if self.push_error:
            raise self.push_error
        self.updates.append((stream_id, payload))


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db(engine):
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        yield session


@pytest.fixture
def opened(db):
    client = Fake()
    load_workspace(client, db, 7)
    return client


def shares(result):
    return {
        o["offer_id"]: (o["share"], o["removed"]) for o in result["offers"]
    }


def test_unopened_stream_is_not_found(db):
    for call in (actions.remove, actions.restore, actions.pin, actions.add):
        with pytest.raises(StreamNotOpenedError):
            call(Fake(), db, 11, 1)
    for call in (actions.cancel, actions.push):
        with pytest.raises(StreamNotOpenedError):
            call(Fake(), db, 11)


def test_add_checks_offer_exists_and_recalculates(opened, db):
    result = actions.add(opened, db, 11, 3)
    assert shares(result) == {1: (34, False), 2: (33, False), 3: (33, False)}
    assert result["dirty"] is True
    assert {o["offer_id"]: o["name"] for o in result["offers"]}[3] == "Offer 3"
    with pytest.raises(OfferNotFoundError):
        actions.add(opened, db, 11, 999)
    # неудачное добавление ничего не изменило
    assert len(load_state(db, 11)[0]) == 3


def test_add_existing_offer_is_editor_error(opened, db):
    with pytest.raises(EditorError):
        actions.add(opened, db, 11, 1)


def test_remove_restore_and_pin_persist(opened, db):
    assert actions.remove(opened, db, 11, 2)["dirty"] is True
    assert load_state(db, 11)[0][1].removed is True
    assert actions.restore(opened, db, 11, 2)["dirty"] is False
    result = actions.pin(opened, db, 11, 1)
    assert result["offers"][0]["pinned"] is True and result["dirty"] is False
    assert load_state(db, 11)[0][0].pinned is True


def test_actions_work_without_offer_names_from_keitaro(opened, db):
    error = KeitaroError(HTTPStatus.INTERNAL_SERVER_ERROR, "boom")
    broken = Fake(offers_error=error)
    result = actions.remove(broken, db, 11, 2)
    assert all(o["name"] is None for o in result["offers"])
    assert shares(result) == {1: (100, False), 2: (0, True)}


def test_cancel_discards_local_changes(opened, db):
    actions.add(opened, db, 11, 3)
    actions.remove(opened, db, 11, 1)
    result = actions.cancel(opened, db, 11)
    assert result["dirty"] is False
    assert shares(result) == {1: (50, False), 2: (50, False)}
    assert opened.updates == []  # Cancel в Keitaro не ходит


def test_push_sends_active_offers_and_becomes_clean(opened, db):
    actions.add(opened, db, 11, 3)
    actions.remove(opened, db, 11, 1)
    result = actions.push(opened, db, 11)
    assert opened.updates == [(11, {"schema": "landings", "offers": [
        {"offer_id": 2, "share": 50, "state": "active"},
        {"offer_id": 3, "share": 50, "state": "active"},
    ]})]
    assert result["dirty"] is False
    working, published = load_state(db, 11)
    assert not is_dirty(working, published)


def test_cancel_after_push_keeps_pushed_state(opened, db):
    actions.add(opened, db, 11, 3)
    actions.push(opened, db, 11)
    actions.remove(opened, db, 11, 1)
    result = actions.cancel(opened, db, 11)
    assert shares(result) == {1: (34, False), 2: (33, False), 3: (33, False)}


def test_push_failure_changes_nothing(opened, db):
    actions.remove(opened, db, 11, 2)
    failing = Fake(push_error=KeitaroError(HTTPStatus.BAD_REQUEST, "bad"))
    with pytest.raises(KeitaroError):
        actions.push(failing, db, 11)
    working, published = load_state(db, 11)
    assert is_dirty(working, published)  # остаётся жёлтым, правки не потеряны


def test_push_of_clean_stream_does_not_call_keitaro(opened, db):
    result = actions.push(opened, db, 11)
    assert result["dirty"] is False and opened.updates == []


def test_push_without_active_offers_is_refused(opened, db):
    actions.remove(opened, db, 11, 1)
    actions.remove(opened, db, 11, 2)
    with pytest.raises(EditorError):
        actions.push(opened, db, 11)
    assert opened.updates == []


def test_offers_payload_skips_removed():
    payload = offers_payload(
        [OfferShare(1, 100), OfferShare(2, 0, removed=True)]
    )
    assert payload == [{"offer_id": 1, "share": 100, "state": "active"}]


# ---- HTTP ----


@pytest.fixture
def api(engine, db, opened):
    maker = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        with maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_client] = lambda: opened
    yield TestClient(app), opened
    app.dependency_overrides.clear()


def test_api_full_cycle(api):
    http, fake = api
    r = http.post("/api/streams/11/offers", json={"offer_id": 3})
    assert r.status_code == HTTPStatus.OK and r.json()["dirty"] is True
    r = http.delete("/api/streams/11/offers/1")
    assert r.status_code == HTTPStatus.OK
    r = http.post("/api/streams/11/offers/1/restore")
    assert r.status_code == HTTPStatus.OK
    r = http.post("/api/streams/11/offers/2/pin")
    assert r.json()["offers"][1]["pinned"] is True
    assert http.post("/api/streams/11/push").json()["dirty"] is False
    assert len(fake.updates) == 1
    assert http.post("/api/streams/11/cancel").status_code == HTTPStatus.OK


def test_api_error_codes(api):
    http, fake = api

    def add(offer_id):
        return http.post("/api/streams/11/offers", json={"offer_id": offer_id})

    not_found = HTTPStatus.NOT_FOUND
    unprocessable = HTTPStatus.UNPROCESSABLE_ENTITY
    assert http.post("/api/streams/99/push").status_code == not_found
    assert http.delete("/api/streams/99/offers/1").status_code == not_found
    assert add(999).status_code == unprocessable
    assert add(0).status_code == unprocessable
    assert add(1).status_code == unprocessable
    r = http.delete("/api/streams/11/offers/777")
    assert r.status_code == unprocessable
    fake.push_error = KeitaroError(HTTPStatus.BAD_REQUEST, "bad")
    http.delete("/api/streams/11/offers/2")
    r = http.post("/api/streams/11/push")
    assert r.status_code == HTTPStatus.BAD_GATEWAY
    assert "bad" in r.json()["detail"]


def test_add_to_unopened_stream_reports_stream_before_offer(db):
    with pytest.raises(StreamNotOpenedError):
        actions.add(Fake(), db, 11, 999)


def test_cancel_is_persisted(opened, db):
    actions.remove(opened, db, 11, 1)
    actions.cancel(opened, db, 11)
    working, published = load_state(db, 11)
    assert not is_dirty(working, published)
    removed = [(o.offer_id, o.removed) for o in working]
    assert removed == [(1, False), (2, False)]
