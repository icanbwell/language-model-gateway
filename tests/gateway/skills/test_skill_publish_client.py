"""Tests for SkillPublishClient."""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from language_model_gateway.gateway.skills.skill_publish_client import (
    SkillPublishClient,
)


@pytest.fixture
def client() -> SkillPublishClient:
    return SkillPublishClient(mcp_server_gateway_url="http://mcp-gateway:5000")


@dataclass
class FakeSSEEvent:
    event: str
    data: str


class FakeEventSource:
    def __init__(self, *, status_code: int, events: list[FakeSSEEvent]) -> None:
        self.response = httpx.Response(status_code=status_code)
        self._events = events

    async def aiter_sse(self) -> AsyncIterator[FakeSSEEvent]:
        for ev in self._events:
            yield ev


@asynccontextmanager
async def _fake_sse(
    *, status_code: int = 200, events: list[FakeSSEEvent] | None = None
) -> AsyncIterator[FakeEventSource]:
    """Produces a context manager matching the aconnect_sse interface."""

    async def _inner(*_args: Any, **_kwargs: Any) -> AsyncIterator[FakeEventSource]:
        yield FakeEventSource(status_code=status_code, events=events or [])

    async for ctx in _inner():
        yield ctx


class TestPublish:
    @pytest.mark.asyncio
    async def test_successful_publish(self, client: SkillPublishClient) -> None:
        events = [
            FakeSSEEvent(event="keepalive", data="{}"),
            FakeSSEEvent(
                event="complete",
                data=json.dumps({"message": "Skill published successfully."}),
            ),
        ]

        @asynccontextmanager
        async def mock_sse(
            *_args: Any, **_kwargs: Any
        ) -> AsyncIterator[FakeEventSource]:
            yield FakeEventSource(status_code=200, events=events)

        with patch(
            "language_model_gateway.gateway.skills.skill_publish_client.aconnect_sse",
            mock_sse,
        ):
            response = await client.publish(
                body={"name": "test-skill", "content": "# Test"},
                auth_header="Bearer token123",
            )

        assert response.status_code == 200
        assert (
            json.loads(bytes(response.body))["message"]
            == "Skill published successfully."
        )

    @pytest.mark.asyncio
    async def test_network_error_returns_502(self, client: SkillPublishClient) -> None:
        @asynccontextmanager
        async def mock_sse(
            *_args: Any, **_kwargs: Any
        ) -> AsyncIterator[FakeEventSource]:
            raise httpx.ConnectError("Connection refused")
            yield FakeEventSource(status_code=500, events=[])  # unreachable

        with patch(
            "language_model_gateway.gateway.skills.skill_publish_client.aconnect_sse",
            mock_sse,
        ):
            response = await client.publish(
                body={"name": "test-skill"},
                auth_header="Bearer token123",
            )

        assert response.status_code == 502

    @pytest.mark.asyncio
    async def test_upstream_error_status_forwarded(
        self, client: SkillPublishClient
    ) -> None:
        @asynccontextmanager
        async def mock_sse(
            *_args: Any, **_kwargs: Any
        ) -> AsyncIterator[FakeEventSource]:
            resp = httpx.Response(
                status_code=422,
                content=json.dumps({"error": "Invalid skill format"}).encode(),
            )
            source = FakeEventSource(status_code=422, events=[])
            source.response = resp
            yield source

        with patch(
            "language_model_gateway.gateway.skills.skill_publish_client.aconnect_sse",
            mock_sse,
        ):
            response = await client.publish(
                body={"name": "bad-skill"},
                auth_header="Bearer token123",
            )

        assert response.status_code == 422
        assert json.loads(bytes(response.body))["error"] == "Invalid skill format"

    @pytest.mark.asyncio
    async def test_sse_error_event_returns_500(
        self, client: SkillPublishClient
    ) -> None:
        events = [
            FakeSSEEvent(event="keepalive", data="{}"),
            FakeSSEEvent(
                event="error",
                data=json.dumps({"error": "Internal server error"}),
            ),
        ]

        @asynccontextmanager
        async def mock_sse(
            *_args: Any, **_kwargs: Any
        ) -> AsyncIterator[FakeEventSource]:
            yield FakeEventSource(status_code=200, events=events)

        with patch(
            "language_model_gateway.gateway.skills.skill_publish_client.aconnect_sse",
            mock_sse,
        ):
            response = await client.publish(
                body={"name": "test-skill"},
                auth_header="Bearer token123",
            )

        assert response.status_code == 500
        assert json.loads(bytes(response.body))["error"] == "Internal server error"

    @pytest.mark.asyncio
    async def test_stream_ends_without_terminal_event(
        self, client: SkillPublishClient
    ) -> None:
        events = [
            FakeSSEEvent(event="keepalive", data="{}"),
            FakeSSEEvent(event="keepalive", data="{}"),
        ]

        @asynccontextmanager
        async def mock_sse(
            *_args: Any, **_kwargs: Any
        ) -> AsyncIterator[FakeEventSource]:
            yield FakeEventSource(status_code=200, events=events)

        with patch(
            "language_model_gateway.gateway.skills.skill_publish_client.aconnect_sse",
            mock_sse,
        ):
            response = await client.publish(
                body={"name": "test-skill"},
                auth_header="Bearer token123",
            )

        assert response.status_code == 502
        assert "terminal event" in json.loads(bytes(response.body))["error"]
