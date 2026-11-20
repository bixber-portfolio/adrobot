"""HTTP-обёртка над действиями редактора потока."""
from collections.abc import Callable
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_client, keitaro_unavailable
from app.keitaro import KeitaroClient, KeitaroError
from app.schemas import AddOfferRequest, StreamEditRead
from app.services import actions
from app.services.actions import StreamNotOpenedError
from app.services.editor import EditorError
from app.services.offers import OfferNotFoundError
from app.services.shares import ShareError

router = APIRouter(prefix="/api/streams", tags=["streams"])

# Ошибки пользователя: запрос понятен, но выполнить его нельзя.
UNPROCESSABLE_ERRORS = (EditorError, ShareError, OfferNotFoundError)


def _run(action: Callable[[], dict]) -> dict:
    """Выполняет действие и переводит ошибки сервисов в HTTP-ответы."""
    try:
        return action()
    except StreamNotOpenedError as error:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail=str(error)
        ) from error
    except UNPROCESSABLE_ERRORS as error:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    except KeitaroError as error:
        raise keitaro_unavailable(error) from error


@router.post("/{stream_id}/offers", response_model=StreamEditRead)
def add_offer(
    stream_id: int,
    data: AddOfferRequest,
    client: KeitaroClient = Depends(get_client),
    db: Session = Depends(get_db),
) -> dict:
    return _run(lambda: actions.add(client, db, stream_id, data.offer_id))


@router.delete(
    "/{stream_id}/offers/{offer_id}", response_model=StreamEditRead
)
def remove_offer(
    stream_id: int,
    offer_id: int,
    client: KeitaroClient = Depends(get_client),
    db: Session = Depends(get_db),
) -> dict:
    return _run(lambda: actions.remove(client, db, stream_id, offer_id))


@router.post(
    "/{stream_id}/offers/{offer_id}/restore", response_model=StreamEditRead
)
def restore_offer(
    stream_id: int,
    offer_id: int,
    client: KeitaroClient = Depends(get_client),
    db: Session = Depends(get_db),
) -> dict:
    return _run(lambda: actions.restore(client, db, stream_id, offer_id))


@router.post(
    "/{stream_id}/offers/{offer_id}/pin", response_model=StreamEditRead
)
def toggle_pin(
    stream_id: int,
    offer_id: int,
    client: KeitaroClient = Depends(get_client),
    db: Session = Depends(get_db),
) -> dict:
    return _run(lambda: actions.pin(client, db, stream_id, offer_id))


@router.post("/{stream_id}/cancel", response_model=StreamEditRead)
def cancel_changes(
    stream_id: int,
    client: KeitaroClient = Depends(get_client),
    db: Session = Depends(get_db),
) -> dict:
    return _run(lambda: actions.cancel(client, db, stream_id))


@router.post("/{stream_id}/push", response_model=StreamEditRead)
def push_stream(
    stream_id: int,
    client: KeitaroClient = Depends(get_client),
    db: Session = Depends(get_db),
) -> dict:
    return _run(lambda: actions.push(client, db, stream_id))
