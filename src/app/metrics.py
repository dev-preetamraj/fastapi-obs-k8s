from __future__ import annotations

import os
import time
from collections.abc import Awaitable, Callable

from prometheus_client import Counter, Gauge, Histogram, Info
from starlette.routing import Match

Receive = Callable[[], Awaitable[dict]]
Send = Callable[[dict], Awaitable[None]]
ASGIApp = Callable[[dict, Receive, Send], Awaitable[None]]

APP_NAME = os.getenv("SERVICE_NAME", "fastapi-obs-k8s")
_BASE_LABELS = ["method", "path", "app_name"]

APP_INFO = Info("fastapi_app", "FastAPI application info")
APP_INFO.info({"app_name": APP_NAME})

REQUESTS = Counter(
    "fastapi_requests_total",
    "Total count of requests by method and path.",
    _BASE_LABELS,
)
RESPONSES = Counter(
    "fastapi_responses_total",
    "Total count of responses by method, path and status codes.",
    ["method", "path", "status_code", "app_name"],
)
REQUESTS_PROCESSING_TIME = Histogram(
    "fastapi_requests_duration_seconds",
    "Histogram of requests processing time by path (in seconds)",
    _BASE_LABELS,
)
EXCEPTIONS = Counter(
    "fastapi_exceptions_total",
    "Total count of exceptions raised by path and exception type",
    ["method", "path", "exception_type", "app_name"],
)
REQUESTS_IN_PROGRESS = Gauge(
    "fastapi_requests_in_progress",
    "Gauge of requests by method and path currently being processed",
    _BASE_LABELS,
)


def _match_route(scope: dict) -> tuple[str, bool]:
    # Resolve to the route template (e.g. /items/{id}) to keep label cardinality
    # bounded — using raw scope["path"] would explode per unique URL.
    app = scope.get("app")
    if app is None:
        return scope.get("path", ""), False
    for route in app.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return route.path, True
    return scope.get("path", ""), False


class PrometheusMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path, is_handled = _match_route(scope)
        method = scope.get("method", "UNKNOWN")

        if path == "/metrics" or not is_handled:
            await self.app(scope, receive, send)
            return

        status_holder = {"code": 500}

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                status_holder["code"] = message["status"]
            await send(message)

        in_progress = REQUESTS_IN_PROGRESS.labels(method=method, path=path, app_name=APP_NAME)
        in_progress.inc()
        REQUESTS.labels(method=method, path=path, app_name=APP_NAME).inc()
        start = time.perf_counter()
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            EXCEPTIONS.labels(
                method=method,
                path=path,
                exception_type=type(exc).__name__,
                app_name=APP_NAME,
            ).inc()
            raise
        finally:
            REQUESTS_PROCESSING_TIME.labels(method=method, path=path, app_name=APP_NAME).observe(
                time.perf_counter() - start
            )
            RESPONSES.labels(
                method=method,
                path=path,
                status_code=str(status_holder["code"]),
                app_name=APP_NAME,
            ).inc()
            in_progress.dec()
