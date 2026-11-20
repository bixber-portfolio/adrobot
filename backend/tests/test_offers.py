from http import HTTPStatus

from fastapi.testclient import TestClient

from app.deps import get_client
from app.keitaro import KeitaroError
from app.main import app
from app.services.offers import search_offers

OFFERS = [
    {"id": 18813, "name": "18813 Flexacil [JOINT-PE]", "state": "active"},
    {"id": 11111, "name": "FitoMishki [Weight Loss]", "state": "active"},
    {"id": 11112, "name": "Oxys [BEAUTY-CL]", "state": "active"},
    {"id": 99, "name": "Old flexacil", "state": "deleted"},
]


def ids(found):
    return [o["id"] for o in found]


def test_empty_query_returns_all_active():
    assert ids(search_offers(OFFERS, "")) == [18813, 11111, 11112]


def test_search_by_id_part():
    assert ids(search_offers(OFFERS, "1111")) == [11111, 11112]


def test_search_by_name_ignores_case_and_spaces():
    assert ids(search_offers(OFFERS, "  FLEXACIL ")) == [18813]


def test_deleted_offers_are_hidden():
    assert 99 not in ids(search_offers(OFFERS, "flexacil"))


def test_limit_and_no_limit():
    assert len(search_offers(OFFERS, "", limit=2)) == 2
    assert len(search_offers(OFFERS, "", limit=None)) == 3


def test_only_id_and_name_are_returned():
    assert set(search_offers(OFFERS, "oxys")[0]) == {"id", "name"}


class FakeClient:
    def __init__(self, fail=False):
        self.fail = fail

    def list_offers(self):
        if self.fail:
            raise KeitaroError(HTTPStatus.FORBIDDEN, "no permission")
        return OFFERS


def call(fake, url):
    app.dependency_overrides[get_client] = lambda: fake
    return TestClient(app).get(url)


def test_api_search():
    r = call(FakeClient(), "/api/offers?q=oxys")
    assert r.status_code == HTTPStatus.OK
    assert r.json() == [{"id": 11112, "name": "Oxys [BEAUTY-CL]"}]


def test_api_limit_validation_and_keitaro_error():
    r = call(FakeClient(), "/api/offers?limit=0")
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    r = call(FakeClient(fail=True), "/api/offers")
    assert r.status_code == HTTPStatus.BAD_GATEWAY
    assert "no permission" in r.json()["detail"]
