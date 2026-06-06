from __future__ import annotations

import structlog
from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.logging_config import configure_logging
from app.metrics import PrometheusMiddleware
from app.middleware.logging import RequestContextMiddleware

configure_logging()

logger = structlog.get_logger()

app = FastAPI()
# Middlewares run outermost-first; RequestContextMiddleware must wrap Prometheus
# so log lines and the metric collection share the same trace_id-bound scope.
app.add_middleware(PrometheusMiddleware)
app.add_middleware(RequestContextMiddleware)
app.mount("/metrics", make_asgi_app())


@app.get("/")
async def root() -> dict[str, str]:
    logger.info("hello")
    return {"message": "Hello World"}
