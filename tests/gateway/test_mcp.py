"""
Tests for MCP (Model Context Protocol) integration.
"""

import pytest
from unittest.mock import AsyncMock, patch

from language_model_gateway.configs.config_schema import MCPServerConfig, HeaderConfig
from language_model_gateway.gateway.mcp import MCPClient, MCPManager, MCPResponse
from language_model_gateway.gateway.oauth import OAuth2TokenManager, OAuth2Token


class TestOAuth2TokenManager:
    """Tests for OAuth2TokenManager"""

    @pytest.mark.asyncio
    async def test_token_creation(self):
        """Test OAuth2 token creation and properties"""
        token = OAuth2Token(
            access_token="test_token", token_type="Bearer", expires_in=3600
        )

        assert token.access_token == "test_token"
        assert token.token_type == "Bearer"
        assert token.authorization_header == "Bearer test_token"
        assert not token.is_expired  # Should not be expired immediately

    @pytest.mark.asyncio
    async def test_token_manager_caching(self):
        """Test that token manager caches tokens correctly"""
        manager = OAuth2TokenManager()

        # Mock the HTTP request
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "access_token": "cached_token",
                "token_type": "Bearer",
                "expires_in": 3600,
            }

            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response

            # First request should make HTTP call
            token1 = await manager.get_token(
                server_name="test_server",
                token_url="https://auth.example.com/token",
                client_id="client_id",
                client_secret="client_secret",
            )

            # Second request should use cached token
            token2 = await manager.get_token(
                server_name="test_server",
                token_url="https://auth.example.com/token",
                client_id="client_id",
                client_secret="client_secret",
            )

            assert token1.access_token == token2.access_token
            # HTTP should only be called once due to caching
            mock_session.return_value.__aenter__.return_value.post.assert_called_once()


class TestMCPClient:
    """Tests for MCPClient"""

    @pytest.fixture
    def mcp_client(self):
        """Create an MCP client for testing"""
        oauth_manager = OAuth2TokenManager()
        return MCPClient(oauth_manager)

    @pytest.fixture
    def sample_config(self):
        """Create a sample MCP server configuration"""
        return MCPServerConfig(
            name="test_server",
            url="http://localhost:8000",
            timeout=30,
            headers=[HeaderConfig(key="User-Agent", value="Test/1.0")],
        )

    @pytest.mark.asyncio
    async def test_add_server(self, mcp_client, sample_config):
        """Test adding a server configuration"""
        await mcp_client.add_server(sample_config)
        assert "test_server" in mcp_client._server_configs
        assert mcp_client._server_configs["test_server"].name == "test_server"

    @pytest.mark.asyncio
    async def test_remove_server(self, mcp_client, sample_config):
        """Test removing a server configuration"""
        await mcp_client.add_server(sample_config)
        await mcp_client.remove_server("test_server")
        assert "test_server" not in mcp_client._server_configs

    @pytest.mark.asyncio
    async def test_oauth_headers(self, mcp_client):
        """Test OAuth2 header generation"""
        config = MCPServerConfig(
            name="oauth_server",
            url="https://api.example.com",
            oauth2_token="static_token",
        )

        await mcp_client.add_server(config)
        headers = await mcp_client._get_auth_headers("oauth_server")

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer static_token"

    @pytest.mark.asyncio
    async def test_list_tools_server_not_configured(self, mcp_client):
        """Test listing tools from unconfigured server"""
        response = await mcp_client.list_tools("nonexistent_server")

        assert not response.success
        assert "not configured" in response.error.lower()
        assert response.server_name == "nonexistent_server"

    @pytest.mark.asyncio
    async def test_http_request_mock(self, mcp_client, sample_config):
        """Test HTTP request with mocked response"""
        await mcp_client.add_server(sample_config)

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "tools": [{"name": "test_tool", "description": "A test tool"}]
            }

            mock_session.return_value.request.return_value.__aenter__.return_value = (
                mock_response
            )
            mcp_client._http_sessions["test_server"] = mock_session.return_value

            response = await mcp_client.list_tools("test_server")

            assert response.success
            assert response.server_name == "test_server"


class TestMCPManager:
    """Tests for MCPManager"""

    @pytest.fixture
    def mcp_manager(self):
        """Create an MCP manager for testing"""
        return MCPManager()

    @pytest.fixture
    def sample_configs(self):
        """Create sample MCP server configurations"""
        return [
            MCPServerConfig(name="server1", url="http://localhost:8001", timeout=30),
            MCPServerConfig(
                name="server2",
                url="http://localhost:8002",
                oauth2_token="test_token",
                timeout=30,
            ),
        ]

    @pytest.mark.asyncio
    async def test_initialization(self, mcp_manager, sample_configs):
        """Test manager initialization with multiple servers"""
        await mcp_manager.initialize(sample_configs)

        assert mcp_manager._initialized
        assert len(mcp_manager.mcp_client._server_configs) == 2

    @pytest.mark.asyncio
    async def test_add_server_success(self, mcp_manager):
        """Test adding a server successfully"""
        config = MCPServerConfig(
            name="new_server", url="http://localhost:9000", timeout=30
        )

        result = await mcp_manager.add_server(config)
        assert result is True

    @pytest.mark.asyncio
    async def test_call_tool_not_initialized(self, mcp_manager):
        """Test calling tool when manager is not initialized"""
        response = await mcp_manager.call_tool(
            server_name="test_server", tool_name="test_tool", arguments={}
        )

        assert not response.success
        assert "not initialized" in response.error.lower()

    @pytest.mark.asyncio
    async def test_get_server_status(self, mcp_manager, sample_configs):
        """Test getting server status"""
        await mcp_manager.initialize(sample_configs)

        with patch.object(mcp_manager.mcp_client, "list_tools") as mock_list_tools:
            mock_list_tools.return_value = MCPResponse(success=True, data=[])

            status = await mcp_manager.get_server_status()

            assert len(status) == 2
            assert "server1" in status
            assert "server2" in status
            assert status["server1"]["connected"] is True

    @pytest.mark.asyncio
    async def test_refresh_oauth_tokens(self, mcp_manager):
        """Test OAuth2 token refresh"""
        config = MCPServerConfig(
            name="oauth_server",
            url="https://api.example.com",
            oauth2_token_url="https://auth.example.com/token",
            oauth2_client_id="client_id",
            oauth2_client_secret="client_secret",
            oauth2_scopes=["read:tools"],
        )

        await mcp_manager.add_server(config)

        with patch.object(mcp_manager.oauth2_manager, "get_token") as mock_get_token:
            mock_get_token.return_value = OAuth2Token(
                access_token="refreshed_token", token_type="Bearer"
            )

            await mcp_manager.refresh_oauth_tokens()

            mock_get_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, mcp_manager, sample_configs):
        """Test manager as async context manager"""
        async with mcp_manager as manager:
            await manager.initialize(sample_configs)
            assert manager._initialized

        # After context exit, should be shut down
        assert not mcp_manager._initialized


class TestMCPIntegration:
    """Integration tests for MCP components"""

    @pytest.mark.asyncio
    async def test_end_to_end_flow(self):
        """Test complete MCP workflow"""
        config = MCPServerConfig(
            name="integration_server", url="http://localhost:8000", timeout=30
        )

        async with MCPManager() as manager:
            # Initialize
            await manager.initialize([config])

            # Mock the HTTP calls
            with patch.object(manager.mcp_client, "_make_http_request") as mock_request:
                # Mock list tools response
                mock_request.return_value = MCPResponse(
                    success=True,
                    data=[{"name": "test_tool", "description": "Test tool"}],
                    server_name="integration_server",
                )

                # List tools
                tools = await manager.list_available_tools("integration_server")
                assert "integration_server" in tools

                # Mock tool call response
                mock_request.return_value = MCPResponse(
                    success=True,
                    data={"result": "Tool executed successfully"},
                    server_name="integration_server",
                )

                # Call tool
                response = await manager.call_tool(
                    server_name="integration_server",
                    tool_name="test_tool",
                    arguments={"param": "value"},
                )

                assert response.success
                assert response.data["result"] == "Tool executed successfully"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
