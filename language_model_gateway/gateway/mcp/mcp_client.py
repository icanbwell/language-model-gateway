import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
import aiohttp

from language_model_gateway.configs.config_schema import MCPServerConfig
from language_model_gateway.gateway.oauth import OAuth2TokenManager

logger = logging.getLogger(__name__)

try:
    # Try to import the actual MCP package when available
    import mcp

    MCP_AVAILABLE = True
    logger.info("MCP package is available")
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP package not found. MCP functionality will use HTTP fallback.")


@dataclass
class MCPResponse:
    """Response from MCP server operations"""

    success: bool
    data: Any = None
    error: Optional[str] = None
    server_name: Optional[str] = None


class MCPClient:
    """
    Client for interacting with Model Context Protocol (MCP) servers.
    Supports OAuth2 authentication and various MCP operations.
    """

    def __init__(self, oauth2_manager: Optional[OAuth2TokenManager] = None):
        """
        Initialize the MCP client.

        Args:
            oauth2_manager: OAuth2 token manager for authentication
        """
        self.oauth2_manager = oauth2_manager or OAuth2TokenManager()
        self._sessions: Dict[str, Any] = {}
        self._server_configs: Dict[str, MCPServerConfig] = {}
        self._http_sessions: Dict[str, aiohttp.ClientSession] = {}

    async def add_server(self, config: MCPServerConfig) -> None:
        """
        Add an MCP server configuration.

        Args:
            config: MCP server configuration
        """
        self._server_configs[config.name] = config
        logger.info(f"Added MCP server configuration: {config.name}")

    async def remove_server(self, server_name: str) -> None:
        """
        Remove an MCP server configuration and close its session.

        Args:
            server_name: Name of the server to remove
        """
        if server_name in self._sessions:
            await self._close_session(server_name)

        if server_name in self._http_sessions:
            await self._http_sessions[server_name].close()
            del self._http_sessions[server_name]

        if server_name in self._server_configs:
            del self._server_configs[server_name]

        logger.info(f"Removed MCP server: {server_name}")

    async def _get_auth_headers(self, server_name: str) -> Dict[str, str]:
        """
        Get authentication headers for a server.

        Args:
            server_name: Name of the server

        Returns:
            Dictionary of headers
        """
        config = self._server_configs[server_name]
        headers = {}

        # Add custom headers
        if config.headers:
            for header in config.headers:
                headers[header.key] = header.value

        # Handle OAuth2 authentication
        if config.oauth2_token:
            headers["Authorization"] = f"Bearer {config.oauth2_token}"
        elif (
            config.oauth2_token_url
            and config.oauth2_client_id
            and config.oauth2_client_secret
        ):
            try:
                token = await self.oauth2_manager.get_token(
                    server_name=server_name,
                    token_url=config.oauth2_token_url,
                    client_id=config.oauth2_client_id,
                    client_secret=config.oauth2_client_secret,
                    scopes=config.oauth2_scopes,
                )
                headers["Authorization"] = token.authorization_header
            except Exception as e:
                logger.error(f"Failed to get OAuth2 token for {server_name}: {e}")
                raise

        return headers

    async def _make_http_request(
        self,
        server_name: str,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> MCPResponse:
        """
        Make an HTTP request to an MCP server.

        Args:
            server_name: Name of the server
            method: HTTP method
            endpoint: API endpoint
            data: Request data

        Returns:
            MCPResponse
        """
        try:
            config = self._server_configs[server_name]
            headers = await self._get_auth_headers(server_name)
            headers["Content-Type"] = "application/json"

            # Create HTTP session if not exists
            if server_name not in self._http_sessions:
                timeout = aiohttp.ClientTimeout(total=config.timeout or 30)
                self._http_sessions[server_name] = aiohttp.ClientSession(
                    timeout=timeout
                )

            session = self._http_sessions[server_name]
            url = f"{config.url.rstrip('/')}/{endpoint.lstrip('/')}"

            async with session.request(
                method, url, headers=headers, json=data if data else None
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return MCPResponse(
                        success=True, data=result, server_name=server_name
                    )
                else:
                    error_text = await response.text()
                    return MCPResponse(
                        success=False,
                        error=f"HTTP {response.status}: {error_text}",
                        server_name=server_name,
                    )
        except Exception as e:
            logger.error(f"HTTP request failed for {server_name}: {e}")
            return MCPResponse(success=False, error=str(e), server_name=server_name)

    async def _close_session(self, server_name: str) -> None:
        """
        Close the session for a server.

        Args:
            server_name: Name of the server
        """
        if server_name in self._sessions:
            session = self._sessions[server_name]
            try:
                if hasattr(session, "close"):
                    if asyncio.iscoroutinefunction(session.close):
                        await session.close()
                    else:
                        session.close()
            except Exception as e:
                logger.warning(f"Error closing session for {server_name}: {e}")
            finally:
                del self._sessions[server_name]

    async def list_tools(self, server_name: str) -> MCPResponse:
        """
        List available tools from an MCP server.

        Args:
            server_name: Name of the server

        Returns:
            MCPResponse with list of tools
        """
        if server_name not in self._server_configs:
            return MCPResponse(
                success=False,
                error=f"Server '{server_name}' not configured",
                server_name=server_name,
            )

        # If MCP library is available and server supports it, use native MCP
        if MCP_AVAILABLE and self._server_configs[server_name].url.startswith(
            "stdio://"
        ):
            # This would be implemented with actual MCP library
            return MCPResponse(
                success=False,
                error="stdio:// MCP servers not yet implemented",
                server_name=server_name,
            )
        else:
            # Use HTTP fallback
            return await self._make_http_request(server_name, "GET", "tools")

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> MCPResponse:
        """
        Call a tool on an MCP server.

        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            MCPResponse with tool execution result
        """
        if server_name not in self._server_configs:
            return MCPResponse(
                success=False,
                error=f"Server '{server_name}' not configured",
                server_name=server_name,
            )

        data = {
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        # If MCP library is available and server supports it, use native MCP
        if MCP_AVAILABLE and self._server_configs[server_name].url.startswith(
            "stdio://"
        ):
            # This would be implemented with actual MCP library
            return MCPResponse(
                success=False,
                error="stdio:// MCP servers not yet implemented",
                server_name=server_name,
            )
        else:
            # Use HTTP fallback
            return await self._make_http_request(server_name, "POST", "call", data)

    async def list_resources(self, server_name: str) -> MCPResponse:
        """
        List available resources from an MCP server.

        Args:
            server_name: Name of the server

        Returns:
            MCPResponse with list of resources
        """
        if server_name not in self._server_configs:
            return MCPResponse(
                success=False,
                error=f"Server '{server_name}' not configured",
                server_name=server_name,
            )

        return await self._make_http_request(server_name, "GET", "resources")

    async def read_resource(self, server_name: str, resource_uri: str) -> MCPResponse:
        """
        Read a resource from an MCP server.

        Args:
            server_name: Name of the server
            resource_uri: URI of the resource to read

        Returns:
            MCPResponse with resource content
        """
        if server_name not in self._server_configs:
            return MCPResponse(
                success=False,
                error=f"Server '{server_name}' not configured",
                server_name=server_name,
            )

        data = {"method": "resources/read", "params": {"uri": resource_uri}}

        return await self._make_http_request(server_name, "POST", "read", data)

    async def list_prompts(self, server_name: str) -> MCPResponse:
        """
        List available prompts from an MCP server.

        Args:
            server_name: Name of the server

        Returns:
            MCPResponse with list of prompts
        """
        if server_name not in self._server_configs:
            return MCPResponse(
                success=False,
                error=f"Server '{server_name}' not configured",
                server_name=server_name,
            )

        return await self._make_http_request(server_name, "GET", "prompts")

    async def get_prompt(
        self,
        server_name: str,
        prompt_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> MCPResponse:
        """
        Get a prompt from an MCP server.

        Args:
            server_name: Name of the server
            prompt_name: Name of the prompt
            arguments: Arguments for the prompt

        Returns:
            MCPResponse with prompt content
        """
        if server_name not in self._server_configs:
            return MCPResponse(
                success=False,
                error=f"Server '{server_name}' not configured",
                server_name=server_name,
            )

        data = {
            "method": "prompts/get",
            "params": {"name": prompt_name, "arguments": arguments or {}},
        }

        return await self._make_http_request(server_name, "POST", "get", data)

    async def close_all_sessions(self) -> None:
        """Close all open sessions."""
        # Close MCP sessions
        for server_name in list(self._sessions.keys()):
            await self._close_session(server_name)

        # Close HTTP sessions
        for session in self._http_sessions.values():
            await session.close()
        self._http_sessions.clear()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_all_sessions()
