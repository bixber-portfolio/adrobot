from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.errors import handle_validation_error
from app.keitaro import get_keitaro_client
from app.routers import campaigns, offers, streams


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.keitaro = get_keitaro_client()
    try:
        yield
    finally:
        app.state.keitaro.close()


app = FastAPI(title="Adrobot", lifespan=lifespan)

app.add_exception_handler(RequestValidationError, handle_validation_error)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaigns.router)
app.include_router(offers.router)
app.include_router(streams.router)
