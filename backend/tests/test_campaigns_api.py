from http import HTTPStatus

from fastapi.testclient import TestClient

from app.config import settings
from app.keitaro import KeitaroError
from app.main import app
from app.routers.campaigns import get_client

URL = "/api/campaigns"


class FakeClient:
    def __init__(self, fail_on_stream=None):
        self.calls = []
        self.fail_on_stream = fail_on_stream
        self.streams = 0

    def list_offers(self):
        return [
            {"id": 1, "name": "One", "state": "active"},
            {"id": 5, "name": "Five", "state": "active"},
        ]

    def create_campaign(self, payload):
        self.calls.append(("campaign", payload))
        return {
            "id": 7,
            "alias": payload["alias"],
            "name": payload["name"],
            "extra": 1,
        }

    def create_stream(self, payload):
        self.streams += 1
        if self.fail_on_stream == self.streams:
            raise KeitaroError(HTTPStatus.BAD_REQUEST, "bad stream")
        self.calls.append(("stream", payload))
        return {"id": self.streams}

    def delete_campaign(self, campaign_id):
        self.calls.append(("delete", campaign_id))


def make(fake):
    app.dependency_overrides[get_client] = lambda: fake
    return TestClient(app)


def post(fake, **body):
    return make(fake).post(URL, json=body)


def test_success():
    fake = FakeClient()
    r = post(fake, name=" X ", geo=" de ", offer_id=5)
    assert r.status_code == HTTPStatus.CREATED, r.text
    assert set(r.json()) == {"id", "alias", "name"}
    assert r.json()["name"] == "X"
    kinds = [c[0] for c in fake.calls]
    assert kinds == ["campaign", "stream", "stream"]
    s1, s2 = fake.calls[1][1], fake.calls[2][1]
    assert s1["filters"][0]["payload"] == ["DE"] and s1["position"] == 1
    assert s2["offers"] == [{"offer_id": 5, "share": 100}]
    assert s2["position"] == 2
    assert s1["action_type"] and s2["action_type"]  # без него Keitaro отвечает 422
    assert fake.calls[0][1]["group_id"] == settings.keitaro_group_id


def test_bad_geo_422():
    for geo in ["Germany", "D", "1A", "ДЕ", ""]:
        r = post(FakeClient(), name="x", geo=geo, offer_id=1)
        assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY, geo


def test_bad_offer_and_name_422():
    r = post(FakeClient(), name="x", geo="DE", offer_id=0)
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    r = post(FakeClient(), name="  ", geo="DE", offer_id=1)
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_keitaro_error_rolls_back_and_502():
    fake = FakeClient(fail_on_stream=2)
    r = post(fake, name="x", geo="DE", offer_id=1)
    assert r.status_code == HTTPStatus.BAD_GATEWAY
    assert "bad stream" in r.json()["detail"]
    assert fake.calls[-1] == ("delete", 7)


def test_unknown_offer_gives_422_and_creates_nothing():
    fake = FakeClient()
    r = post(fake, name="x", geo="DE", offer_id=222)
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert "222" in r.json()["detail"]
    assert fake.calls == []
