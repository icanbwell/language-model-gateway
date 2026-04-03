import logging
from typing import Protocol

from languagemodelcommon.configs.schemas.config_schema import McpOAuthConfig
from oidcauthlib.auth.well_known_configuration.auth_server_metadata import (  # type: ignore[import-not-found]
    AuthServerMetadata,
)
from oidcauthlib.auth.well_known_configuration.auth_server_metadata_discovery import (  # type: ignore[import-not-found]
    AuthServerMetadataDiscovery as OidcAuthServerMetadataDiscovery,
    AuthServerMetadataDiscoveryProtocol as OidcDiscoveryProtocol,
)

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["MCP"])


class McpAuthServerDiscoveryProtocol(Protocol):
    """Discovers OAuth metadata for an MCP server and returns an McpOAuthConfig."""

    async def discover(self, *, mcp_server_url: str) -> McpOAuthConfig | None: ...


class McpAuthServerDiscovery:
    """Thin wrapper that delegates to oidc-auth-lib's AuthServerMetadataDiscovery
    and maps the result to McpOAuthConfig for use in the MCP gateway."""

    def __init__(  # type: ignore[no-any-unimported]
        self,
        *,
        discovery: OidcDiscoveryProtocol | None = None,
    ) -> None:
        self._discovery = discovery or OidcAuthServerMetadataDiscovery()

    @staticmethod
    def _to_mcp_oauth_config(metadata: AuthServerMetadata) -> McpOAuthConfig:  # type: ignore[no-any-unimported]
        return McpOAuthConfig.model_validate(
            {
                "authorization_url": metadata.authorization_endpoint,
                "token_url": metadata.token_endpoint,
                "registration_url": metadata.registration_endpoint,
                "issuer": metadata.issuer,
                "scopes": metadata.scopes_supported,
            }
        )

    async def discover(self, *, mcp_server_url: str) -> McpOAuthConfig | None:
        result = await self._discovery.discover(resource_url=mcp_server_url)
        if result is None:
            return None

        config = self._to_mcp_oauth_config(result)
        logger.info(
            "Mapped discovered auth server metadata to McpOAuthConfig for %s",
            mcp_server_url,
        )
        return config
