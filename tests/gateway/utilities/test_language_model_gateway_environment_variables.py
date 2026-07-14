"""
Tests for LanguageModelGatewayEnvironmentVariables.model_routing_bedrock_transport.
"""

from __future__ import annotations

import pytest

from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)


def test_model_routing_bedrock_transport_defaults_to_mantle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODEL_ROUTING_BEDROCK_TRANSPORT", raising=False)
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_transport == "mantle"


def test_model_routing_bedrock_transport_reads_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_ROUTING_BEDROCK_TRANSPORT", "native")
    env_vars = LanguageModelGatewayEnvironmentVariables()
    assert env_vars.model_routing_bedrock_transport == "native"
