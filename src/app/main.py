from __future__ import annotations

import structlog
from fastapi import FastAPI

from app.logging_config import configure_logging
from app.middleware.logging import RequestContextMiddleware

configure_logging()

logger = structlog.get_logger()

app = FastAPI()
app.add_middleware(RequestContextMiddleware)


@app.get("/")
async def root() -> dict[str, str]:
    logger.info("hello")
    return {"message": "Hello World"}
