from http import HTTPStatus

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.deps import get_client
from app.keitaro import KeitaroError
from app.main import app
from app.services.snapshots import merge_keitaro
from app.services.streams import (
    build_stream_views,
    clicks_by_stream,
    clicks_report_payload,
    offers_from_stream,
)

CAMPAIGN_ID = 216076

REDIRECT = {
    "id": 10,
    "name": "EN -> Google",
    "position": 1,
    "schema": "redirect",
    "action_payload": "https://www.google.com",
    "offers": [],
}
LANDINGS = {
    "id": 11,
    "name": "Offer 222",
    "position": 2,
    "schema": "landings",
    "offers": [
        {"offer_id": 222, "share": 60, "state": "active"},
        {"offer_id": 18813, "share": 40, "state": "active"},
        {"offer_id": 5, "share": 25, "state": "disabled"},
    ],
}


def test_offers_from_stream_marks_inactive_as_removed_with_zero_share():
    offers = offers_from_stream(LANDINGS)
    assert [(o.offer_id, o.share, o.removed) for o in offers] == [
        (222, 60, False), (18813, 40, False), (5, 0, True)
    ]


def test_clicks_by_stream_is_tolerant():
    report = {"rows": [
        {"stream_id": "11", "clicks": "7"},
        {"clicks": 3},
        {"stream_id": 12, "clicks": None},
    ]}
    assert clicks_by_stream(report) == {11: 7}
    assert clicks_by_stream({"rows": []}) == {}
    assert clicks_by_stream(None) == {}


def test_report_payload_targets_campaign_and_today():
    payload = clicks_report_payload(CAMPAIGN_ID)
    assert payload["range"] == {"interval": "today"}
    assert payload["filters"][0]["expression"] == CAMPAIGN_ID
    assert payload["dimensions"] == ["stream_id"]


def states_for(*streams):
    return {
        s["id"]: merge_keitaro(None, [], offers_from_stream(s))
        for s in streams
    }


def test_views_list_all_streams_sorted_with_flags_names_and_clicks():
    first = {**LANDINGS, "id": 12, "position": 0, "name": "First"}
    views = build_stream_views(
        [LANDINGS, REDIRECT, first],
        states_for(LANDINGS, first),
        {222: "Offer A"},
        {11: 4},
    )
    assert [v["id"] for v in views] == [12, 10, 11]
    redirect, landings = views[1], views[2]
    assert redirect["editable"] is False
    assert redirect["stream_schema"] == "redirect"
    assert redirect["offers"] == [] and redirect["dirty"] is False
    assert landings["editable"] is True
    assert landings["clicks_today"] == 4 and views[0]["clicks_today"] == 0
    assert landings["offers"][0]["name"] == "Offer A"
    assert landings["offers"][1]["name"] is None


def test_views_without_statistics():
    views = build_stream_views([LANDINGS], states_for(LANDINGS), {}, None)
    assert views[0]["clicks_today"] is None


class FakeClient:
    def __init__(self, streams_error=None, report_error=None):
        self.streams_error = streams_error
        self.report_error = report_error

    def get_campaign_streams(self, campaign_id):
        if self.streams_error:
            raise self.streams_error
        return [REDIRECT, LANDINGS]

    def list_offers(self):
        return [{"id": 222, "name": "Offer A", "state": "active"}]

    def build_report(self, payload):
        if self.report_error:
            raise self.report_error
        return {"rows": [{"stream_id": 11, "clicks": 2}]}


def get(fake, campaign_id=CAMPAIGN_ID):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        with maker() as session:
            yield session

    app.dependency_overrides[get_client] = lambda: fake
    app.dependency_overrides[get_db] = override_db
    return TestClient(app).get(f"/api/campaigns/{campaign_id}/streams")


def test_api_returns_streams_and_link_to_keitaro():
    r = get(FakeClient())
    assert r.status_code == HTTPStatus.OK, r.text
    body = r.json()
    assert body["keitaro_url"].endswith(
        f"/admin/#!/campaign/{CAMPAIGN_ID}/main"
    )
    assert [s["id"] for s in body["streams"]] == [10, 11]
    landings = body["streams"][1]
    assert landings["clicks_today"] == 2
    assert landings["offers"][0] == {
        "offer_id": 222,
        "name": "Offer A",
        "share": 60,
        "pinned": False,
        "removed": False,
    }
    assert landings["dirty"] is False


def test_api_report_failure_does_not_break_page():
    error = KeitaroError(HTTPStatus.FORBIDDEN, "no access")
    r = get(FakeClient(report_error=error))
    assert r.status_code == HTTPStatus.OK
    assert r.json()["streams"][1]["clicks_today"] is None


def test_api_unknown_campaign_is_404_and_other_errors_502():
    not_found = KeitaroError(HTTPStatus.NOT_FOUND, "not found")
    r = get(FakeClient(streams_error=not_found))
    assert r.status_code == HTTPStatus.NOT_FOUND
    boom = KeitaroError(HTTPStatus.INTERNAL_SERVER_ERROR, "boom")
    r = get(FakeClient(streams_error=boom))
    assert r.status_code == HTTPStatus.BAD_GATEWAY
    assert "boom" in r.json()["detail"]


def test_empty_stream_is_editable_whatever_its_schema():
    empty = {"id": 13, "name": "Empty", "position": 3, "schema": "redirect",
             "action_payload": "", "offers": []}
    views = build_stream_views([REDIRECT, empty], {}, {}, None)
    assert [(v["id"], v["editable"]) for v in views] == [
        (10, False), (13, True)
    ]


def test_stream_with_offers_or_target_url_is_not_treated_as_empty():
    from app.services.streams import is_empty
    assert is_empty({"offers": [], "action_payload": ""}) is True
    assert is_empty({"offers": [], "action_payload": "https://a.b"}) is False
    assert is_empty({"offers": [{"offer_id": 1}]}) is False
