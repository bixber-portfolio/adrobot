from http import HTTPStatus

from fastapi import HTTPException, Request

from app.keitaro import KeitaroClient, KeitaroError


def get_client(request: Request) -> KeitaroClient:
    return request.app.state.keitaro


def keitaro_unavailable(error: KeitaroError) -> HTTPException:
    """Ошибка Keitaro для клиента нашего API: 502, Keitaro подвёл."""
    return HTTPException(status_code=HTTPStatus.BAD_GATEWAY, detail=str(error))
