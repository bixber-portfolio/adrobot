from http import HTTPStatus

from fastapi.testclient import TestClient

from app.deps import get_client
from app.keitaro import KeitaroError
from app.main import app
from app.services.campaign_search import search_campaigns

CAMPAIGNS = [
    {"id": 5, "name": "Germany Casino", "alias": "abc123", "state": "active"},
    {"id": 20, "name": "France Nutra", "alias": "zzz999", "state": "active"},
    {"id": 31, "name": "bixber_test_DE", "alias": "qwe456",
     "state": "deleted"},
    {"id": 40, "name": "Spain", "alias": "germ77", "state": "disabled"},
    {"id": 41, "name": None, "alias": None},
]


def ids(found):
    return [c["id"] for c in found]


def test_empty_query_returns_all_but_archived_newest_first():
    assert ids(search_campaigns(CAMPAIGNS)) == [41, 40, 20, 5]


def test_search_by_name_alias_and_id_ignores_case_and_spaces():
    assert ids(search_campaigns(CAMPAIGNS, "  GERM ")) == [40, 5]
    assert ids(search_campaigns(CAMPAIGNS, "zzz")) == [20]
    assert ids(search_campaigns(CAMPAIGNS, "20")) == [20]
    assert search_campaigns(CAMPAIGNS, "nothing") == []


def test_archived_campaigns_are_never_found():
    assert search_campaigns(CAMPAIGNS, "bixber") == []
    assert search_campaigns(CAMPAIGNS, "31") == []


def test_limit_and_missing_fields():
    assert ids(search_campaigns(CAMPAIGNS, limit=2)) == [41, 40]
    last = search_campaigns(CAMPAIGNS, "41")[0]
    assert last == {"id": 41, "name": "", "alias": "", "state": "active"}
    assert len(search_campaigns(CAMPAIGNS, limit=None)) == 4


class FakeClient:
    def __init__(self, error=None):
        self.error = error

    def list_campaigns(self):
        if self.error:
            raise self.error
        return CAMPAIGNS


def get(fake, query=""):
    app.dependency_overrides[get_client] = lambda: fake
    return TestClient(app).get(f"/api/campaigns{query}")


def test_api_returns_matches():
    r = get(FakeClient(), "?q=germ&limit=5")
    assert r.status_code == HTTPStatus.OK
    assert [c["id"] for c in r.json()] == [40, 5]
    assert set(r.json()[0]) == {"id", "name", "alias", "state"}


def test_api_keitaro_error_is_502():
    error = KeitaroError(HTTPStatus.INTERNAL_SERVER_ERROR, "boom")
    r = get(FakeClient(error))
    assert r.status_code == HTTPStatus.BAD_GATEWAY
    assert "boom" in r.json()["detail"]


def test_api_limit_is_validated_with_readable_message():
    r = get(FakeClient(), "?limit=0")
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert r.json()["detail"] == "Поле «Лимит» не может быть меньше 1"
