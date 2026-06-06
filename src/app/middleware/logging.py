from __future__ import annotations

import re
import secrets
import time
from collections.abc import Awaitable, Callable

import structlog

Receive = Callable[[], Awaitable[dict]]
Send = Callable[[dict], Awaitable[None]]
ASGIApp = Callable[[dict, Receive, Send], Awaitable[None]]

_TRACEPARENT_RE = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-[0-9a-f]{2}$")

log = structlog.get_logger()


def _extract_trace_ids(traceparent: str | None) -> tuple[str, str]:
    if traceparent:
        match = _TRACEPARENT_RE.match(traceparent.strip().lower())
        if match:
            return match.group(1), secrets.token_hex(8)
    return secrets.token_hex(16), secrets.token_hex(8)


def _header_value(scope: dict, name: bytes) -> str | None:
    for key, value in scope.get("headers", ()):
        if key == name:
            return value.decode("latin-1")
    return None


def _client_ip(scope: dict) -> str | None:
    client = scope.get("client")
    return client[0] if client else None


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        traceparent = _header_value(scope, b"traceparent")
        trace_id, span_id = _extract_trace_ids(traceparent)

        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            span_id=span_id,
            method=scope.get("method"),
            path=scope.get("path"),
            client_ip=_client_ip(scope),
        )

        log.info("request.started")

        status_holder = {"code": 500}
        start = time.perf_counter()

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                status_holder["code"] = message["status"]
                headers = list(message.get("headers") or [])
                headers.append((b"x-trace-id", trace_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            log.exception("request.failed")
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log.info(
                "request.finished",
                status_code=status_holder["code"],
                duration_ms=duration_ms,
            )
            structlog.contextvars.clear_contextvars()
