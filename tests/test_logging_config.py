from __future__ import annotations

import json
import logging

import pytest
import structlog

from app.logging_config import configure_logging


@pytest.fixture(autouse=True)
def _reset_logging():
    yield
    logging.getLogger().handlers.clear()
    structlog.reset_defaults()


def test_json_format_emits_parseable_json_with_required_keys(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("SERVICE_NAME", "test-service")

    configure_logging()
    structlog.get_logger().info("hello", trace_id="a" * 32, span_id="b" * 16)

    out = capsys.readouterr().out.strip().splitlines()
    assert out, "no log output"

    payload = json.loads(out[-1])
    for key in ("timestamp", "level", "event", "service", "trace_id", "span_id"):
        assert key in payload, f"missing key: {key} in {payload}"

    assert payload["service"] == "test-service"
    assert payload["event"] == "hello"


def test_console_format_does_not_crash_and_produces_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setenv("LOG_FORMAT", "console")

    configure_logging()
    structlog.get_logger().info("console-smoke")

    captured = capsys.readouterr().out
    assert "console-smoke" in captured


def test_stdlib_logger_routed_through_structlog_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    configure_logging()
    logging.getLogger("uvicorn.error").info("uvicorn-message")

    out = capsys.readouterr().out.strip().splitlines()
    payload = json.loads(out[-1])
    assert payload["event"] == "uvicorn-message"
