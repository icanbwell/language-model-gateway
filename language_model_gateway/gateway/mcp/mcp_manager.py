import logging
from typing import Dict, List, Any, Optional

from language_model_gateway.configs.config_schema import MCPServerConfig
from language_model_gateway.gateway.mcp.mcp_client import MCPClient, MCPResponse
from language_model_gateway.gateway.oauth import OAuth2TokenManager

logger = logging.getLogger(__name__)


class MCPManager:
    """
    Manager for MCP (Model Context Protocol) servers.
    Handles server configurations, client connections, and operations.
    """

    def __init__(self):
        """Initialize the MCP manager."""
        self.oauth2_manager = OAuth2TokenManager()
        self.mcp_client = MCPClient(self.oauth2_manager)
        self._initialized = False

    async def initialize(self, server_configs: List[MCPServerConfig]) -> None:
        """
        Initialize the MCP manager with server configurations.

        Args:
            server_configs: List of MCP server configurations
        """
        try:
            for config in server_configs:
                await self.mcp_client.add_server(config)
                logger.info(f"Initialized MCP server: {config.name}")

            self._initialized = True
            logger.info(f"MCP Manager initialized with {len(server_configs)} servers")
        except Exception as e:
            logger.error(f"Failed to initialize MCP Manager: {e}")
            raise

    async def add_server(self, config: MCPServerConfig) -> bool:
        """
        Add a new MCP server configuration.

        Args:
            config: MCP server configuration

        Returns:
            True if server was added successfully
        """
        try:
            await self.mcp_client.add_server(config)
            logger.info(f"Added MCP server: {config.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add MCP server {config.name}: {e}")
            return False

    async def remove_server(self, server_name: str) -> bool:
        """
        Remove an MCP server.

        Args:
            server_name: Name of the server to remove

        Returns:
            True if server was removed successfully
        """
        try:
            await self.mcp_client.remove_server(server_name)
            logger.info(f"Removed MCP server: {server_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove MCP server {server_name}: {e}")
            return False

    async def list_available_tools(
        self, server_name: Optional[str] = None
    ) -> Dict[str, List[Any]]:
        """
        List available tools from MCP servers.

        Args:
            server_name: Optional specific server name. If None, lists from all servers.

        Returns:
            Dictionary mapping server names to their available tools
        """
        results = {}

        if server_name:
            response = await self.mcp_client.list_tools(server_name)
            if response.success:
                results[server_name] = response.data or []
            else:
                logger.error(
                    f"Failed to list tools from {server_name}: {response.error}"
                )
                results[server_name] = []
        else:
            # List tools from all configured servers
            for config_name in self.mcp_client._server_configs:
                response = await self.mcp_client.list_tools(config_name)
                if response.success:
                    results[config_name] = response.data or []
                else:
                    logger.error(
                        f"Failed to list tools from {config_name}: {response.error}"
                    )
                    results[config_name] = []

        return results

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
        if not self._initialized:
            return MCPResponse(
                success=False,
                error="MCP Manager not initialized",
                server_name=server_name,
            )

        logger.info(f"Calling tool {tool_name} on server {server_name}")
        return await self.mcp_client.call_tool(server_name, tool_name, arguments)

    async def list_available_resources(
        self, server_name: Optional[str] = None
    ) -> Dict[str, List[Any]]:
        """
        List available resources from MCP servers.

        Args:
            server_name: Optional specific server name. If None, lists from all servers.

        Returns:
            Dictionary mapping server names to their available resources
        """
        results = {}

        if server_name:
            response = await self.mcp_client.list_resources(server_name)
            if response.success:
                results[server_name] = response.data or []
            else:
                logger.error(
                    f"Failed to list resources from {server_name}: {response.error}"
                )
                results[server_name] = []
        else:
            # List resources from all configured servers
            for config_name in self.mcp_client._server_configs:
                response = await self.mcp_client.list_resources(config_name)
                if response.success:
                    results[config_name] = response.data or []
                else:
                    logger.error(
                        f"Failed to list resources from {config_name}: {response.error}"
                    )
                    results[config_name] = []

        return results

    async def read_resource(self, server_name: str, resource_uri: str) -> MCPResponse:
        """
        Read a resource from an MCP server.

        Args:
            server_name: Name of the server
            resource_uri: URI of the resource to read

        Returns:
            MCPResponse with resource content
        """
        if not self._initialized:
            return MCPResponse(
                success=False,
                error="MCP Manager not initialized",
                server_name=server_name,
            )

        logger.info(f"Reading resource {resource_uri} from server {server_name}")
        return await self.mcp_client.read_resource(server_name, resource_uri)

    async def list_available_prompts(
        self, server_name: Optional[str] = None
    ) -> Dict[str, List[Any]]:
        """
        List available prompts from MCP servers.

        Args:
            server_name: Optional specific server name. If None, lists from all servers.

        Returns:
            Dictionary mapping server names to their available prompts
        """
        results = {}

        if server_name:
            response = await self.mcp_client.list_prompts(server_name)
            if response.success:
                results[server_name] = response.data or []
            else:
                logger.error(
                    f"Failed to list prompts from {server_name}: {response.error}"
                )
                results[server_name] = []
        else:
            # List prompts from all configured servers
            for config_name in self.mcp_client._server_configs:
                response = await self.mcp_client.list_prompts(config_name)
                if response.success:
                    results[config_name] = response.data or []
                else:
                    logger.error(
                        f"Failed to list prompts from {config_name}: {response.error}"
                    )
                    results[config_name] = []

        return results

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
        if not self._initialized:
            return MCPResponse(
                success=False,
                error="MCP Manager not initialized",
                server_name=server_name,
            )

        logger.info(f"Getting prompt {prompt_name} from server {server_name}")
        return await self.mcp_client.get_prompt(server_name, prompt_name, arguments)

    async def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status information for all configured servers.

        Returns:
            Dictionary with server status information
        """
        status = {}

        for server_name in self.mcp_client._server_configs:
            try:
                # Try to list tools as a health check
                response = await self.mcp_client.list_tools(server_name)
                status[server_name] = {
                    "connected": response.success,
                    "error": response.error if not response.success else None,
                    "config": self.mcp_client._server_configs[server_name].model_dump(),
                }
            except Exception as e:
                status[server_name] = {
                    "connected": False,
                    "error": str(e),
                    "config": self.mcp_client._server_configs[server_name].model_dump(),
                }

        return status

    async def refresh_oauth_tokens(self) -> None:
        """Refresh OAuth2 tokens for all servers that use OAuth2 authentication."""
        logger.info("Refreshing OAuth2 tokens for MCP servers")

        for server_name, config in self.mcp_client._server_configs.items():
            if (
                config.oauth2_token_url
                and config.oauth2_client_id
                and config.oauth2_client_secret
            ):
                try:
                    await self.oauth2_manager.get_token(
                        server_name=server_name,
                        token_url=config.oauth2_token_url,
                        client_id=config.oauth2_client_id,
                        client_secret=config.oauth2_client_secret,
                        scopes=config.oauth2_scopes,
                        force_refresh=True,
                    )
                    logger.info(f"Refreshed OAuth2 token for server: {server_name}")
                except Exception as e:
                    logger.error(
                        f"Failed to refresh OAuth2 token for {server_name}: {e}"
                    )

    async def shutdown(self) -> None:
        """Shutdown the MCP manager and close all connections."""
        logger.info("Shutting down MCP Manager")
        await self.mcp_client.close_all_sessions()
        self.oauth2_manager.clear_all_tokens()
        self._initialized = False

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
