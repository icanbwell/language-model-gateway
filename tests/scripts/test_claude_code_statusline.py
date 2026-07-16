"""
Tests for language_model_gateway/static/claude_code_statusline.py.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "language_model_gateway"
    / "static"
    / "claude_code_statusline.py"
)
_spec = importlib.util.spec_from_file_location("claude_code_statusline", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
statusline = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(statusline)


class TestFormatSavingsLine:
    def test_formats_total_and_tier_breakdown(self) -> None:
        payload = {
            "total_savings_usd": 0.42,
            "tiers": {
                "low": {"cost_usd": 0.10, "backend": "aws_bedrock"},
                "medium": {"cost_usd": 0.30, "backend": "anthropic"},
                "high": {"cost_usd": 0.02, "backend": "aws_bedrock"},
            },
        }
        line = statusline.format_savings_line(payload)
        assert line is not None
        assert "0.42" in line
        assert "costs:" in line
        assert "Haiku(AWS) $0.10" in line
        assert "Sonnet(Anthropic) $0.30" in line
        assert "Opus(AWS) $0.02" in line

    def test_shows_placeholder_when_tier_backend_unknown(self) -> None:
        """A tier recorded before backend tracking shipped (or any other
        missing-backend case) shows a "?" placeholder rather than guessing
        or omitting the provider tag silently."""
        payload = {
            "total_savings_usd": 0.10,
            "tiers": {"medium": {"cost_usd": 0.23}},
        }
        line = statusline.format_savings_line(payload)
        assert line is not None
        assert "Sonnet(?) $0.23" in line

    def test_formats_total_with_no_tiers(self) -> None:
        payload = {"total_savings_usd": 0.0, "tiers": {}}
        line = statusline.format_savings_line(payload)
        assert line is not None
        assert "0.00" in line

    def test_returns_none_when_total_missing(self) -> None:
        assert statusline.format_savings_line({}) is None

    def test_returns_none_when_total_savings_is_string(self) -> None:
        """Malformed field type: total_savings_usd is a string instead of number."""
        payload = {"total_savings_usd": "not-a-number", "tiers": {}}
        assert statusline.format_savings_line(payload) is None

    def test_returns_none_when_tier_cost_is_string(self) -> None:
        """Malformed field type: cost_usd within a tier is a string instead of number."""
        payload = {
            "total_savings_usd": 0.42,
            "tiers": {
                "low": {"cost_usd": "nope"},
                "medium": {"cost_usd": 0.30},
            },
        }
        assert statusline.format_savings_line(payload) is None

    def test_returns_none_when_tiers_is_not_dict(self) -> None:
        """Malformed field type: tiers is a non-dict value (e.g., string)."""
        payload = {"total_savings_usd": 0.42, "tiers": "not-a-dict"}
        assert statusline.format_savings_line(payload) is None


class TestFetchSavings:
    def test_returns_none_on_url_error(self) -> None:
        with patch.object(
            statusline.urllib.request,
            "urlopen",
            side_effect=statusline.urllib.error.URLError("boom"),
        ):
            result = statusline.fetch_savings("http://gateway", "sess-1")
        assert result is None

    def test_returns_none_on_malformed_json(self) -> None:
        response = io.BytesIO(b"not json")
        cm = patch.object(statusline.urllib.request, "urlopen")
        with cm as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = response
            result = statusline.fetch_savings("http://gateway", "sess-1")
        assert result is None

    def test_returns_parsed_json_on_success(self) -> None:
        payload = {"total_savings_usd": 0.42, "tiers": {}}
        response = io.BytesIO(json.dumps(payload).encode())
        cm = patch.object(statusline.urllib.request, "urlopen")
        with cm as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = response
            result = statusline.fetch_savings("http://gateway", "sess-1")
        assert result == payload


class TestMain:
    def test_prints_nothing_when_stdin_is_not_json(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with patch.object(sys, "stdin", io.StringIO("not json")):
            statusline.main()
        assert capsys.readouterr().out == ""

    def test_prints_nothing_when_session_id_missing(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with patch.object(sys, "stdin", io.StringIO(json.dumps({}))):
            statusline.main()
        assert capsys.readouterr().out == ""

    @pytest.mark.parametrize("stdin_value", [None, [], "sess-1", 42])
    def test_prints_nothing_when_stdin_is_valid_json_but_not_an_object(
        self, capsys: pytest.CaptureFixture[str], stdin_value: object
    ) -> None:
        """Valid JSON that isn't a dict (null, list, string, number) must not crash main()."""
        with patch.object(sys, "stdin", io.StringIO(json.dumps(stdin_value))):
            statusline.main()
        assert capsys.readouterr().out == ""

    def test_prints_nothing_when_gateway_url_unset(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("MODEL_ROUTING_GATEWAY_URL", raising=False)
        with patch.object(
            sys, "stdin", io.StringIO(json.dumps({"session_id": "sess-1"}))
        ):
            statusline.main()
        assert capsys.readouterr().out == ""

    def test_prints_line_on_success(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MODEL_ROUTING_GATEWAY_URL", "http://gateway")
        payload = {"total_savings_usd": 0.42, "tiers": {}}
        with patch.object(
            sys, "stdin", io.StringIO(json.dumps({"session_id": "sess-1"}))
        ):
            with patch.object(statusline, "fetch_savings", return_value=payload):
                statusline.main()
        assert "0.42" in capsys.readouterr().out
