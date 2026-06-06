from __future__ import annotations

import structlog
from fastapi import FastAPI

from app.logging_config import configure_logging
from app.middleware.logging import RequestContextMiddleware

configure_logging()

log = structlog.get_logger()

app = FastAPI()
app.add_middleware(RequestContextMiddleware)


@app.get("/")
async def root() -> dict[str, str]:
    log.info("hello")
    return {"message": "Hello World"}
