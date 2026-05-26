import logging
from enum import Enum
from typing import Annotated, Any, Dict, Sequence

from fastapi import APIRouter, Depends, HTTPException
from fastapi import params
from starlette.requests import Request
from starlette.responses import JSONResponse

from oidcauthlib.auth.auth_manager import AuthManager
from oidcauthlib.auth.token_reader import TokenReader
from languagemodelcommon.configs.config_reader.config_reader import ConfigReader
from languagemodelcommon.configs.schemas.config_schema import AgentConfig
from languagemodelcommon.mcp.mcp_client.mcp_app_proxy import (
    McpProxyToolCallRequest,
    McpProxyResourceReadRequest,
    proxy_tool_call,
    proxy_resource_read,
)
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from simple_container.container.inject import Inject
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class McpProxyRouter:
    """Router for proxying MCP tool/resource calls from app iframes."""

    def __init__(
        self,
        *,
        prefix: str = "/api/v1/mcp-proxy",
        tags: list[str | Enum] | None = None,
        dependencies: Sequence[params.Depends] | None = None,
    ) -> None:
        self.prefix = prefix
        self.tags = tags or ["mcp-proxy"]
        self.dependencies = dependencies or []
        self.router = APIRouter(
            prefix=self.prefix, tags=self.tags, dependencies=self.dependencies
        )
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            "/tools/call",
            self.proxy_tools_call,
            methods=["POST"],
            response_model=None,
            summary="Proxy a tools/call request from an MCP App iframe",
            status_code=200,
        )
        self.router.add_api_route(
            "/resources/read",
            self.proxy_resources_read,
            methods=["POST"],
            response_model=None,
            summary="Proxy a resources/read request from an MCP App iframe",
            status_code=200,
        )

    def get_router(self) -> APIRouter:
        return self.router

    @staticmethod
    async def _verify_auth(
        request: Request,
        token_reader: TokenReader,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
    ) -> str:
        """Extract and verify the bearer token, returning the raw token string.

        Raises HTTPException(401) if the token is missing or invalid.
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid Authorization header",
            )

        token: str | None = token_reader.extract_token(authorization_header=auth_header)
        if not token:
            raise HTTPException(status_code=401, detail="Could not extract token")

        # Allow dev bypass tokens
        if token not in ("bedrock", "fake-api-key"):
            token_item = await token_reader.verify_token_async(token=token)
            if token_item is None:
                raise HTTPException(status_code=401, detail="Invalid or expired token")

        return token

    async def proxy_tools_call(
        self,
        request: Request,
        body: Dict[str, Any],
        token_reader: Annotated[TokenReader, Depends(Inject(TokenReader))],
        auth_manager: Annotated[AuthManager, Depends(Inject(AuthManager))],
        config_reader: Annotated[ConfigReader, Depends(Inject(ConfigReader))],
        environment_variables: Annotated[
            LanguageModelGatewayEnvironmentVariables,
            Depends(Inject(LanguageModelGatewayEnvironmentVariables)),
        ],
    ) -> JSONResponse:
        """Proxy a tools/call from an MCP App iframe to the MCP server."""
        await self._verify_auth(request, token_reader, environment_variables)

        tool_name = body.get("name")
        arguments = body.get("arguments", {})
        server_name = body.get("server")

        if not tool_name:
            raise HTTPException(status_code=400, detail="Missing 'name' field")

        agent_config = await self._resolve_agent_config(
            config_reader=config_reader,
            tool_name=tool_name,
            server_name=server_name,
        )
        if agent_config is None:
            raise HTTPException(
                status_code=404,
                detail=f"No MCP server found for tool '{tool_name}'",
            )

        try:
            result = await proxy_tool_call(
                McpProxyToolCallRequest(
                    tool_name=tool_name,
                    arguments=arguments,
                    server_url=agent_config.url or "",
                )
            )
            return JSONResponse(content=result)
        except Exception as e:
            logger.error("MCP proxy tools/call failed for %s: %s", tool_name, e)
            raise HTTPException(status_code=502, detail=str(e))

    async def proxy_resources_read(
        self,
        request: Request,
        body: Dict[str, Any],
        token_reader: Annotated[TokenReader, Depends(Inject(TokenReader))],
        auth_manager: Annotated[AuthManager, Depends(Inject(AuthManager))],
        config_reader: Annotated[ConfigReader, Depends(Inject(ConfigReader))],
        environment_variables: Annotated[
            LanguageModelGatewayEnvironmentVariables,
            Depends(Inject(LanguageModelGatewayEnvironmentVariables)),
        ],
    ) -> JSONResponse:
        """Proxy a resources/read from an MCP App iframe to the MCP server."""
        await self._verify_auth(request, token_reader, environment_variables)

        uri = body.get("uri")
        server_name = body.get("server")

        if not uri:
            raise HTTPException(status_code=400, detail="Missing 'uri' field")

        agent_config = await self._resolve_agent_config(
            config_reader=config_reader,
            tool_name=None,
            server_name=server_name,
        )
        if agent_config is None:
            raise HTTPException(
                status_code=404,
                detail=f"No MCP server found for resource '{uri}'",
            )

        try:
            result = await proxy_resource_read(
                McpProxyResourceReadRequest(
                    uri=uri,
                    server_url=agent_config.url or "",
                )
            )
            return JSONResponse(content=result)
        except Exception as e:
            logger.error("MCP proxy resources/read failed for %s: %s", uri, e)
            raise HTTPException(status_code=502, detail=str(e))

    @staticmethod
    async def _resolve_agent_config(
        *,
        config_reader: ConfigReader,
        tool_name: str | None,
        server_name: str | None,
    ) -> AgentConfig | None:
        """Find the AgentConfig for a tool or server name.

        Resolution order:
        1. Exact server_name match (highest priority — caller's explicit selection)
        2. Tool name match (fallback when server_name not provided or not found)
        """
        configs = await config_reader.read_model_configs_async()

        if server_name:
            for config in configs:
                for agent in config.get_agents():
                    if agent.name == server_name:
                        return agent

        if tool_name:
            for config in configs:
                for agent in config.get_agents():
                    if not agent.tools:
                        continue
                    agent_tool_names = [t.strip() for t in agent.tools.split(",")]
                    if tool_name in agent_tool_names:
                        return agent

        return None
