"""Понятные пользователю сообщения вместо технических ошибок Pydantic."""
from http import HTTPStatus

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

VALUE_ERROR_PREFIX = "Value error, "
WHOLE_REQUEST = "запрос"

FIELD_TITLES = {
    "name": "Название",
    "geo": "Гео",
    "offer_id": "Оффер",
    "campaign_id": "Номер кампании",
    "stream_id": "Номер потока",
    "limit": "Лимит",
}

# Шаблоны по типу ошибки Pydantic; в них подставляются поле и параметры.
MESSAGES = {
    "missing": "Поле «{field}» обязательно",
    "string_too_long": "Поле «{field}»: не больше {max_length} символов",
    "string_type": "Поле «{field}» должно быть текстом",
    "int_parsing": "Поле «{field}» должно быть целым числом",
    "int_type": "Поле «{field}» должно быть целым числом",
    "int_from_float": "Поле «{field}» должно быть целым числом",
    "greater_than": "Поле «{field}» должно быть больше {gt}",
    "greater_than_equal": "Поле «{field}» не может быть меньше {ge}",
    "less_than_equal": "Поле «{field}» не может быть больше {le}",
    "json_invalid": "Запрос содержит некорректный JSON",
}
EMPTY_STRING_MESSAGE = "Поле «{field}» не может быть пустым"
DEFAULT_MESSAGE = "Поле «{field}»: некорректное значение"


def _field_title(location: tuple) -> str:
    names = [part for part in location if isinstance(part, str)][1:]
    if not names:
        return WHOLE_REQUEST
    return FIELD_TITLES.get(names[-1], names[-1])


def error_message(error: dict) -> str:
    """Одна ошибка проверки данных, переведённая на человеческий язык."""
    kind = error["type"]
    if kind == "value_error":
        return error["msg"].removeprefix(VALUE_ERROR_PREFIX)
    context = error.get("ctx") or {}
    if kind == "string_too_short" and context.get("min_length") == 1:
        template = EMPTY_STRING_MESSAGE
    else:
        template = MESSAGES.get(kind, DEFAULT_MESSAGE)
    field = _field_title(tuple(error["loc"]))
    return template.format(field=field, **context)


async def handle_validation_error(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    detail = "; ".join(error_message(item) for item in error.errors())
    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content={"detail": detail},
    )
