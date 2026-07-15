"""
Tests for LanguageModelGatewayEnvironmentVariables.model_routing_bedrock_transport
and model_routing_qwen_enable_thinking.
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
