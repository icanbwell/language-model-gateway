import logging
from typing import Any, Dict, List

from oidcauthlib.auth.auth_manager import AuthManager
from oidcauthlib.auth.config.auth_config import AuthConfig
from oidcauthlib.auth.config.auth_config_reader import AuthConfigReader
from oidcauthlib.auth.models.auth import AuthInformation

from language_model_gateway.configs.config_schema import (
    AgentConfig,
    ChatModelConfig,
    AuthenticationConfig,
)
from language_model_gateway.gateway.auth.models.token_cache_item import TokenCacheItem
from language_model_gateway.gateway.auth.tools.tool_auth_manager import ToolAuthManager
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class PassThroughTokenManager:
    def __init__(
        self,
        *,
        auth_manager: AuthManager,
        auth_config_reader: AuthConfigReader,
        tool_auth_manager: ToolAuthManager,
    ) -> None:
        self.auth_manager: AuthManager = auth_manager
        if self.auth_manager is None:
            raise ValueError("auth_manager must not be None")
        if not isinstance(self.auth_manager, AuthManager):
            raise TypeError("auth_manager must be an instance of AuthManager")

        self.auth_config_reader: AuthConfigReader = auth_config_reader
        if self.auth_config_reader is None:
            raise ValueError("auth_config_reader must not be None")
        if not isinstance(self.auth_config_reader, AuthConfigReader):
            raise TypeError(
                "auth_config_reader must be an instance of AuthConfigReader"
            )

        self.tool_auth_manager: ToolAuthManager = tool_auth_manager
        if self.tool_auth_manager is None:
            raise ValueError("tool_auth_manager must not be None")
        if not isinstance(self.tool_auth_manager, ToolAuthManager):
            raise TypeError("tool_auth_manager must be an instance of ToolAuthManager")

    async def check_tokens_are_valid_for_tools(
        self,
        *,
        auth_information: AuthInformation,
        headers: Dict[str, Any],
        model_config: ChatModelConfig,
    ) -> None:
        tools_using_authentication: List[AgentConfig] = (
            [a for a in model_config.get_agents() if a.auth == "jwt_token"]
            if model_config.get_agents() is not None
            else []
        )
        if not tools_using_authentication:
            logger.debug("No tools require authentication.")
            return

        auth_headers = [
            headers.get(key) for key in headers if key.lower() == "authorization"
        ]
        auth_header: str | None = auth_headers[0] if auth_headers else None
        for tool_using_authentication in tools_using_authentication:
            await self.check_tokens_are_valid_for_tool(
                auth_header=auth_header,
                auth_information=auth_information,
                authentication_config=tool_using_authentication,
            )

    async def check_tokens_are_valid_for_tool(
        self,
        *,
        auth_header: str | None,
        auth_information: AuthInformation,
        authentication_config: AuthenticationConfig,
    ) -> TokenCacheItem | None:
        tool_auth_providers: list[str] | None = authentication_config.auth_providers
        if (
            authentication_config.auth_providers is None
            or len(authentication_config.auth_providers) == 0
        ):
            logger.debug(
                f"Tool {authentication_config.name} doesn't have auth providers."
            )
            return None
        if not auth_information.redirect_uri:
            logger.debug("AuthInformation doesn't have redirect_uri.")
            return None

        tool_first_auth_provider: str | None = (
            tool_auth_providers[0] if tool_auth_providers is not None else None
        )
        auth_config: AuthConfig | None = (
            self.auth_config_reader.get_config_for_auth_provider(
                auth_provider=tool_first_auth_provider
            )
            if tool_first_auth_provider is not None
            else None
        )
        if auth_config is None:
            raise ValueError(
                f"AuthConfig not found for auth provider {tool_first_auth_provider}"
                f" used by tool {authentication_config.name}."
            )
        if not auth_information.subject:
            logger.error(
                f"AuthInformation doesn't have subject: {auth_information} in token: {auth_header}"
            )
            raise ValueError(
                "AuthInformation must have subject to authenticate for tools."
                + (f"{auth_information}" if logger.isEnabledFor(logging.DEBUG) else "")
            )
        if not tool_first_auth_provider:
            raise ValueError("Tool using authentication must have an auth provider.")
        tool_client_id: str | None = (
            auth_config.client_id if auth_config is not None else None
        )
        if not tool_client_id:
            raise ValueError("Tool using authentication must have a client ID.")

        authorization_url: (
            str | None
        ) = await self.auth_manager.create_authorization_url(
            auth_provider=tool_first_auth_provider,
            redirect_uri=auth_information.redirect_uri,
            url=authentication_config.url,
            referring_email=auth_information.email,
            referring_subject=auth_information.subject,
        )
        error_message: str = (
            f"\nFollowing tools require authentication: {authentication_config.name}."
            + f"\nClick here to [Login to {auth_config.friendly_name}]({authorization_url})."
        )
        return await self.tool_auth_manager.get_token_for_tool_async(
            auth_header=auth_header,
            error_message=error_message,
            tool_config=authentication_config,
        )
