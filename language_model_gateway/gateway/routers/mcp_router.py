import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel

from language_model_gateway.configs.config_schema import MCPServerConfig
from language_model_gateway.gateway.mcp import MCPManager

logger = logging.getLogger(__name__)

# Create the router
mcp_router = APIRouter(prefix="/mcp", tags=["MCP"])

# Global MCP manager instance
mcp_manager: Optional[MCPManager] = None


class MCPServerConfigRequest(BaseModel):
    """Request model for adding MCP server configuration"""

    name: str
    url: str
    oauth2_token: Optional[str] = None
    oauth2_token_url: Optional[str] = None
    oauth2_client_id: Optional[str] = None
    oauth2_client_secret: Optional[str] = None
    oauth2_scopes: Optional[List[str]] = None
    timeout: Optional[int] = 30
    headers: Optional[Dict[str, str]] = None


class ToolCallRequest(BaseModel):
    """Request model for calling MCP tools"""

    server_name: str
    tool_name: str
    arguments: Dict[str, Any]


class ResourceReadRequest(BaseModel):
    """Request model for reading MCP resources"""

    server_name: str
    resource_uri: str


class PromptGetRequest(BaseModel):
    """Request model for getting MCP prompts"""

    server_name: str
    prompt_name: str
    arguments: Optional[Dict[str, Any]] = None


async def get_mcp_manager() -> MCPManager:
    """Dependency to get the MCP manager instance"""
    global mcp_manager
    if mcp_manager is None:
        mcp_manager = MCPManager()
    return mcp_manager


@mcp_router.post("/servers", status_code=status.HTTP_201_CREATED)
async def add_server(
    config_request: MCPServerConfigRequest,
    manager: MCPManager = Depends(get_mcp_manager),
) -> Dict[str, Any]:
    """
    Add a new MCP server configuration.
    """
    try:
        # Convert headers dict to HeaderConfig list if provided
        headers = None
        if config_request.headers:
            from language_model_gateway.configs.config_schema import HeaderConfig

            headers = [
                HeaderConfig(key=k, value=v) for k, v in config_request.headers.items()
            ]

        config = MCPServerConfig(
            name=config_request.name,
            url=config_request.url,
            oauth2_token=config_request.oauth2_token,
            oauth2_token_url=config_request.oauth2_token_url,
            oauth2_client_id=config_request.oauth2_client_id,
            oauth2_client_secret=config_request.oauth2_client_secret,
            oauth2_scopes=config_request.oauth2_scopes,
            timeout=config_request.timeout,
            headers=headers,
        )

        success = await manager.add_server(config)
        if success:
            return {"message": f"Server '{config.name}' added successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to add server '{config.name}'",
            )
    except Exception as e:
        logger.error(f"Error adding MCP server: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@mcp_router.delete("/servers/{server_name}")
async def remove_server(
    server_name: str, manager: MCPManager = Depends(get_mcp_manager)
) -> Dict[str, Any]:
    """
    Remove an MCP server configuration.
    """
    try:
        success = await manager.remove_server(server_name)
        if success:
            return {"message": f"Server '{server_name}' removed successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server '{server_name}' not found",
            )
    except Exception as e:
        logger.error(f"Error removing MCP server: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@mcp_router.get("/servers/status")
async def get_server_status(
    manager: MCPManager = Depends(get_mcp_manager),
) -> Dict[str, Any]:
    """
    Get status information for all configured MCP servers.
    """
    try:
        status_info = await manager.get_server_status()
        return {"servers": status_info}
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@mcp_router.get("/tools")
async def list_tools(
    server_name: Optional[str] = None, manager: MCPManager = Depends(get_mcp_manager)
) -> Dict[str, Any]:
    """
    List available tools from MCP servers.
    """
    try:
        tools = await manager.list_available_tools(server_name)
        return {"tools": tools}
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@mcp_router.post("/tools/call")
async def call_tool(
    request: ToolCallRequest, manager: MCPManager = Depends(get_mcp_manager)
) -> Dict[str, Any]:
    """
    Call a tool on an MCP server.
    """
    try:
        response = await manager.call_tool(
            request.server_name, request.tool_name, request.arguments
        )

        if response.success:
            return {
                "success": True,
                "data": response.data,
                "server_name": response.server_name,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=response.error
            )
    except Exception as e:
        logger.error(f"Error calling tool: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@mcp_router.get("/resources")
async def list_resources(
    server_name: Optional[str] = None, manager: MCPManager = Depends(get_mcp_manager)
) -> Dict[str, Any]:
    """
    List available resources from MCP servers.
    """
    try:
        resources = await manager.list_available_resources(server_name)
        return {"resources": resources}
    except Exception as e:
        logger.error(f"Error listing resources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@mcp_router.post("/resources/read")
async def read_resource(
    request: ResourceReadRequest, manager: MCPManager = Depends(get_mcp_manager)
) -> Dict[str, Any]:
    """
    Read a resource from an MCP server.
    """
    try:
        response = await manager.read_resource(
            request.server_name, request.resource_uri
        )

        if response.success:
            return {
                "success": True,
                "data": response.data,
                "server_name": response.server_name,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=response.error
            )
    except Exception as e:
        logger.error(f"Error reading resource: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@mcp_router.get("/prompts")
async def list_prompts(
    server_name: Optional[str] = None, manager: MCPManager = Depends(get_mcp_manager)
) -> Dict[str, Any]:
    """
    List available prompts from MCP servers.
    """
    try:
        prompts = await manager.list_available_prompts(server_name)
        return {"prompts": prompts}
    except Exception as e:
        logger.error(f"Error listing prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@mcp_router.post("/prompts/get")
async def get_prompt(
    request: PromptGetRequest, manager: MCPManager = Depends(get_mcp_manager)
) -> Dict[str, Any]:
    """
    Get a prompt from an MCP server.
    """
    try:
        response = await manager.get_prompt(
            request.server_name, request.prompt_name, request.arguments
        )

        if response.success:
            return {
                "success": True,
                "data": response.data,
                "server_name": response.server_name,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=response.error
            )
    except Exception as e:
        logger.error(f"Error getting prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@mcp_router.post("/oauth/refresh")
async def refresh_oauth_tokens(
    manager: MCPManager = Depends(get_mcp_manager),
) -> Dict[str, Any]:
    """
    Refresh OAuth2 tokens for all MCP servers.
    """
    try:
        await manager.refresh_oauth_tokens()
        return {"message": "OAuth2 tokens refreshed successfully"}
    except Exception as e:
        logger.error(f"Error refreshing OAuth2 tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
