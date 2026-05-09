"""Tests for SkillPublishClient."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from language_model_gateway.gateway.skills.skill_publish_client import (
    SkillPublishClient,
)


@pytest.fixture
def client() -> SkillPublishClient:
    return SkillPublishClient(mcp_server_gateway_url="http://mcp-gateway:5000")


class TestPublish:
    @pytest.mark.asyncio
    async def test_successful_publish(self, client: SkillPublishClient) -> None:
        mock_response = httpx.Response(
            status_code=200,
            json={"status": "published", "url": "https://github.com/org/repo/pr/1"},
        )
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            response = await client.publish(
                body={"name": "test-skill", "content": "# Test"},
                auth_header="Bearer token123",
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_network_error_returns_502(self, client: SkillPublishClient) -> None:
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")
            response = await client.publish(
                body={"name": "test-skill"},
                auth_header="Bearer token123",
            )

        assert response.status_code == 502

    @pytest.mark.asyncio
    async def test_upstream_error_forwarded(self, client: SkillPublishClient) -> None:
        mock_response = httpx.Response(
            status_code=422,
            json={"error": "Invalid skill format"},
        )
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            response = await client.publish(
                body={"name": "bad-skill"},
                auth_header="Bearer token123",
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_non_json_response_handled(self, client: SkillPublishClient) -> None:
        mock_response = httpx.Response(
            status_code=500,
            text="Internal Server Error",
        )
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            response = await client.publish(
                body={"name": "test-skill"},
                auth_header="Bearer token123",
            )

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_posts_to_correct_url(self, client: SkillPublishClient) -> None:
        mock_response = httpx.Response(status_code=200, json={"status": "ok"})
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            await client.publish(
                body={"name": "my-skill"},
                auth_header="Bearer abc",
            )

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        expected_url = "http://mcp-gateway:5000/api/skills/publish"
        actual_url = (
            call_args.args[0] if call_args.args else call_args.kwargs.get("url")
        )
        assert actual_url == expected_url
