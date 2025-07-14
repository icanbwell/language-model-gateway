"""
Example usage of the MCP client and manager for the Language Model Gateway.

This example demonstrates how to:
1. Configure MCP servers with OAuth2 authentication
2. Call tools and read resources from MCP servers
3. Integrate with the existing language model gateway
"""

import asyncio
import logging
from typing import Dict, Any

from language_model_gateway.configs.config_schema import MCPServerConfig, HeaderConfig
from language_model_gateway.gateway.mcp import MCPManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_mcp_usage():
    """Example of using MCP servers with OAuth2 authentication."""

    # Create MCP manager
    async with MCPManager() as mcp_manager:
        # Example 1: Basic HTTP MCP server without authentication
        basic_server_config = MCPServerConfig(
            name="basic_mcp_server", url="http://localhost:8000", timeout=30
        )

        # Example 2: MCP server with static OAuth2 token
        oauth_static_config = MCPServerConfig(
            name="oauth_static_server",
            url="https://api.example.com/mcp",
            oauth2_token="your_static_token_here",
            timeout=30,
        )

        # Example 3: MCP server with dynamic OAuth2 token
        oauth_dynamic_config = MCPServerConfig(
            name="oauth_dynamic_server",
            url="https://api.example.com/mcp",
            oauth2_token_url="https://auth.example.com/oauth/token",
            oauth2_client_id="your_client_id",
            oauth2_client_secret="your_client_secret",
            oauth2_scopes=["read:tools", "execute:tools"],
            timeout=30,
            headers=[
                HeaderConfig(key="User-Agent", value="LanguageModelGateway/1.0"),
                HeaderConfig(key="Accept", value="application/json"),
            ],
        )

        # Example 4: MCP server with custom headers
        custom_headers_config = MCPServerConfig(
            name="custom_headers_server",
            url="https://internal.company.com/mcp",
            headers=[
                HeaderConfig(key="API-Key", value="your_api_key"),
                HeaderConfig(key="X-Request-Source", value="language-gateway"),
            ],
            timeout=60,
        )

        # Initialize the manager with server configurations
        configs = [
            basic_server_config,
            oauth_static_config,
            oauth_dynamic_config,
            custom_headers_config,
        ]

        await mcp_manager.initialize(configs)

        # List available tools from all servers
        logger.info("Listing available tools from all MCP servers...")
        all_tools = await mcp_manager.list_available_tools()
        for server_name, tools in all_tools.items():
            logger.info(f"Server '{server_name}' has {len(tools)} tools")

        # Example: Call a specific tool
        logger.info("Calling a tool on the basic MCP server...")
        tool_response = await mcp_manager.call_tool(
            server_name="basic_mcp_server",
            tool_name="database_query",
            arguments={"query": "SELECT * FROM users WHERE active = true", "limit": 10},
        )

        if tool_response.success:
            logger.info(f"Tool call successful: {tool_response.data}")
        else:
            logger.error(f"Tool call failed: {tool_response.error}")

        # Example: List and read resources
        logger.info("Listing available resources...")
        all_resources = await mcp_manager.list_available_resources(
            "oauth_dynamic_server"
        )
        for server_name, resources in all_resources.items():
            logger.info(f"Server '{server_name}' has {len(resources)} resources")

        # Example: Read a specific resource
        resource_response = await mcp_manager.read_resource(
            server_name="oauth_dynamic_server",
            resource_uri="file://documents/user_manual.md",
        )

        if resource_response.success:
            logger.info(f"Resource read successful: {resource_response.data}")
        else:
            logger.error(f"Resource read failed: {resource_response.error}")

        # Example: Get server status
        logger.info("Getting server status...")
        status = await mcp_manager.get_server_status()
        for server_name, server_status in status.items():
            logger.info(
                f"Server '{server_name}': Connected={server_status['connected']}"
            )

        # Example: Refresh OAuth2 tokens
        logger.info("Refreshing OAuth2 tokens...")
        await mcp_manager.refresh_oauth_tokens()

        logger.info("MCP example completed successfully!")


def create_sample_config() -> Dict[str, Any]:
    """
    Create a sample configuration for MCP servers.
    This could be added to the main configuration schema.
    """
    return {
        "mcp_servers": [
            {"name": "database_tools", "url": "http://localhost:8001", "timeout": 30},
            {
                "name": "file_operations",
                "url": "https://api.fileservice.com/mcp",
                "oauth2_token_url": "https://auth.fileservice.com/oauth/token",
                "oauth2_client_id": "${FILE_SERVICE_CLIENT_ID}",
                "oauth2_client_secret": "${FILE_SERVICE_CLIENT_SECRET}",
                "oauth2_scopes": ["read:files", "write:files"],
                "timeout": 45,
                "headers": [{"key": "User-Agent", "value": "LanguageModelGateway/1.0"}],
            },
            {
                "name": "external_api_tools",
                "url": "https://external-api.example.com/mcp",
                "oauth2_token": "${EXTERNAL_API_TOKEN}",
                "timeout": 60,
                "headers": [
                    {"key": "X-API-Version", "value": "v1"},
                    {"key": "Accept", "value": "application/json"},
                ],
            },
        ]
    }


if __name__ == "__main__":
    # Run the example
    asyncio.run(example_mcp_usage())

    # Print sample configuration
    print("\nSample MCP Configuration:")
    import json

    print(json.dumps(create_sample_config(), indent=2))
