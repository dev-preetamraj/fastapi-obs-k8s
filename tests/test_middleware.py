from __future__ import annotations

import re

import pytest
import structlog
from httpx import AsyncClient

HEX_32 = re.compile(r"^[0-9a-f]{32}$")
VALID_TRACEPARENT_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
VALID_TRACEPARENT = f"00-{VALID_TRACEPARENT_ID}-00f067aa0ba902b7-01"


async def test_no_traceparent_generates_fresh_trace_id(client: AsyncClient) -> None:
    resp = await client.get("/ping")

    assert resp.status_code == 200
    trace_id = resp.headers["x-trace-id"]
    assert HEX_32.match(trace_id), f"not 32 hex chars: {trace_id!r}"


async def test_valid_traceparent_is_reused(client: AsyncClient) -> None:
    resp = await client.get("/ping", headers={"traceparent": VALID_TRACEPARENT})

    assert resp.headers["x-trace-id"] == VALID_TRACEPARENT_ID


@pytest.mark.parametrize(
    "bad",
    ["garbage", "00-short-00f067aa0ba902b7-01", "ZZ-" + "f" * 32 + "-" + "f" * 16 + "-01"],
)
async def test_malformed_traceparent_falls_back_to_fresh_id(client: AsyncClient, bad: str) -> None:
    resp = await client.get("/ping", headers={"traceparent": bad})

    assert resp.status_code == 200
    assert HEX_32.match(resp.headers["x-trace-id"])


async def test_response_always_carries_x_trace_id(client: AsyncClient) -> None:
    resp = await client.get("/ping")
    assert "x-trace-id" in resp.headers


async def test_exception_path_logs_request_failed_and_reraises(
    client: AsyncClient,
) -> None:
    with structlog.testing.capture_logs() as logs, pytest.raises(RuntimeError, match="boom"):
        await client.get("/boom")

    events = [entry["event"] for entry in logs]
    assert "request.started" in events
    assert "request.failed" in events
    assert "request.finished" in events

    failed = next(e for e in logs if e["event"] == "request.failed")
    assert failed["log_level"] == "error"
    assert "exc_info" in failed or "exception" in failed


async def test_sequential_requests_have_distinct_trace_ids(client: AsyncClient) -> None:
    first = await client.get("/ping")
    second = await client.get("/ping")

    assert first.headers["x-trace-id"] != second.headers["x-trace-id"]


async def test_contextvars_cleared_between_requests(client: AsyncClient) -> None:
    await client.get("/ping")
    assert structlog.contextvars.get_contextvars() == {}
