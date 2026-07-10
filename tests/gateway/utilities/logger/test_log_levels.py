"""Tests for build_json_log_formatter and build_log_handler.

Groundcover splits stdout on every newline, so a multi-line log message or
traceback becomes multiple log entries. These tests verify each record
renders as exactly one line of valid JSON, regardless of message content.
"""

from __future__ import annotations

import json
import logging
import sys
from types import TracebackType
from typing import Any

import pytest
import structlog

from language_model_gateway.gateway.utilities.logger.log_levels import (
    build_json_log_formatter,
    build_log_handler,
)

ExcInfo = tuple[type[BaseException], BaseException, TracebackType | None]


def _make_record(
    message: str,
    *,
    exc_info: ExcInfo | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test_log_levels.py",
        lineno=42,
        msg=message,
        args=None,
        exc_info=exc_info,
    )
    if extra_fields is not None:
        record.extra_fields = extra_fields
    return record


def test_json_log_formatter_produces_single_line_valid_json() -> None:
    formatter = build_json_log_formatter()
    record = _make_record("hello world")

    output = formatter.format(record)

    assert "\n" not in output
    payload = json.loads(output)
    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.logger"
    assert payload["line"] == 42


def test_json_log_formatter_escapes_embedded_newlines() -> None:
    formatter = build_json_log_formatter()
    record = _make_record("line1\nline2\nline3")

    output = formatter.format(record)

    assert "\n" not in output
    payload = json.loads(output)
    assert payload["message"] == "line1\nline2\nline3"


def test_json_log_formatter_folds_exception_into_single_line() -> None:
    formatter = build_json_log_formatter()
    try:
        raise ValueError("boom")
    except ValueError:
        exc_info = sys.exc_info()
        assert exc_info[0] is not None and exc_info[1] is not None
        record = _make_record(
            "failed", exc_info=(exc_info[0], exc_info[1], exc_info[2])
        )

    output = formatter.format(record)

    assert "\n" not in output
    payload = json.loads(output)
    assert "ValueError: boom" in payload["exception"]
    assert "exc_info" not in payload


def test_json_log_formatter_merges_extra_fields() -> None:
    formatter = build_json_log_formatter()
    record = _make_record(
        "request handled",
        extra_fields={"request_id": "req-123", "duration_ms": 42.5},
    )

    output = formatter.format(record)

    payload = json.loads(output)
    assert payload["request_id"] == "req-123"
    assert payload["duration_ms"] == 42.5


def test_build_log_handler_defaults_to_json_formatter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    handler = build_log_handler()
    assert isinstance(handler.formatter, structlog.stdlib.ProcessorFormatter)


def test_build_log_handler_uses_text_formatter_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOG_FORMAT", "text")
    handler = build_log_handler()
    assert not isinstance(handler.formatter, structlog.stdlib.ProcessorFormatter)
    assert isinstance(handler.formatter, logging.Formatter)
