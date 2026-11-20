from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from app.deps import get_client
from app.errors import error_message
from app.main import app

URL = "/api/campaigns"
VALID = {"name": "x", "geo": "DE", "offer_id": 1}


@pytest.fixture(autouse=True)
def no_keitaro():
    """Проверка данных не должна доходить до Keitaro, клиент не нужен."""
    app.dependency_overrides[get_client] = lambda: None


def post(**changes):
    body = {**VALID, **changes}
    body = {k: v for k, v in body.items() if v is not ...}
    return TestClient(app).post(URL, json=body)


@pytest.mark.parametrize("changes, expected", [
    ({"geo": "1A"},
     "Гео должно быть двухбуквенным кодом страны, например DE"),
    ({"geo": "Germany"},
     "Гео должно быть двухбуквенным кодом страны, например DE"),
    ({"name": ""}, "Поле «Название» не может быть пустым"),
    ({"name": "  "}, "Поле «Название» не может быть пустым"),
    ({"name": "x" * 201}, "Поле «Название»: не больше 200 символов"),
    ({"offer_id": 0}, "Поле «Оффер» должно быть больше 0"),
    ({"offer_id": "abc"}, "Поле «Оффер» должно быть целым числом"),
    ({"geo": ...}, "Поле «Гео» обязательно"),
])
def test_validation_errors_are_readable(changes, expected):
    r = post(**changes)
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert r.json() == {"detail": expected}


def test_several_errors_are_joined_and_have_no_technical_words():
    detail = post(geo="1", name="", offer_id=0).json()["detail"]
    assert detail.count(";") == 2
    for technical in ("Value error", "Input should", "String should"):
        assert technical not in detail


def test_path_parameter_error():
    r = TestClient(app).get("/api/campaigns/abc/streams")
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert r.json()["detail"] == (
        "Поле «Номер кампании» должно быть целым числом"
    )


def test_unknown_error_type_falls_back_to_generic_message():
    error = {"type": "something_new", "loc": ("body", "geo"), "msg": "x"}
    assert error_message(error) == "Поле «Гео»: некорректное значение"
    whole = {"type": "something_new", "loc": ("body",), "msg": "x"}
    assert error_message(whole) == "Поле «запрос»: некорректное значение"
