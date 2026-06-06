from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.logging import RequestContextMiddleware


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    application.add_middleware(RequestContextMiddleware)

    @application.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "true"}

    @application.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
