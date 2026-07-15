"""
Tests for LanguageModelGatewayEnvironmentVariables.model_routing_bedrock_transport,
model_routing_qwen_enable_thinking, and the native-Bedrock client timeout
properties.
"""

from __future__ import annotations

import pytest

from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)


def test_model_routing_bedrock_transport_defaults_to_native(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODEL_ROUTING_BEDROCK_TRANSPORT", raising=False)
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_transport == "native"


def test_model_routing_bedrock_transport_reads_mantle_opt_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_ROUTING_BEDROCK_TRANSPORT", "mantle")
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_transport == "mantle"


def test_model_routing_bedrock_transport_is_case_insensitive_for_mantle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_ROUTING_BEDROCK_TRANSPORT", "MANTLE")
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_transport == "mantle"


def test_model_routing_bedrock_transport_unknown_value_falls_back_to_native(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Anything other than literally "mantle" — including a typo — must not
    silently land on Mantle, the less reliable transport."""
    monkeypatch.setenv("MODEL_ROUTING_BEDROCK_TRANSPORT", "native")
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_transport == "native"

    monkeypatch.setenv("MODEL_ROUTING_BEDROCK_TRANSPORT", "mantel")
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_transport == "native"


def test_model_routing_qwen_enable_thinking_defaults_to_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODEL_ROUTING_QWEN_ENABLE_THINKING", raising=False)
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_qwen_enable_thinking is True


def test_model_routing_qwen_enable_thinking_reads_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_ROUTING_QWEN_ENABLE_THINKING", "false")
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_qwen_enable_thinking is False


def test_model_routing_bedrock_connect_timeout_seconds_defaults_to_60(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODEL_ROUTING_BEDROCK_CONNECT_TIMEOUT_SECONDS", raising=False)
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_connect_timeout_seconds == 60.0


def test_model_routing_bedrock_connect_timeout_seconds_reads_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_ROUTING_BEDROCK_CONNECT_TIMEOUT_SECONDS", "10")
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_connect_timeout_seconds == 10.0


def test_model_routing_bedrock_read_timeout_seconds_defaults_to_60(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODEL_ROUTING_BEDROCK_READ_TIMEOUT_SECONDS", raising=False)
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_read_timeout_seconds == 60.0


def test_model_routing_bedrock_read_timeout_seconds_reads_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_ROUTING_BEDROCK_READ_TIMEOUT_SECONDS", "300")
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_read_timeout_seconds == 300.0


def test_model_routing_bedrock_max_attempts_defaults_to_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODEL_ROUTING_BEDROCK_MAX_ATTEMPTS", raising=False)
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_max_attempts == 1


def test_model_routing_bedrock_max_attempts_reads_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_ROUTING_BEDROCK_MAX_ATTEMPTS", "3")
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_max_attempts == 3


def test_model_routing_bedrock_retry_mode_defaults_to_adaptive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODEL_ROUTING_BEDROCK_RETRY_MODE", raising=False)
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_retry_mode == "adaptive"


def test_model_routing_bedrock_retry_mode_reads_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_ROUTING_BEDROCK_RETRY_MODE", "standard")
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_retry_mode == "standard"
