import logging
from typing import override, Any, Dict

from oidcauthlib.auth.config.auth_config import AuthConfig
from oidcauthlib.auth.config.auth_config_reader import AuthConfigReader
from oidcauthlib.auth.fastapi_auth_manager import FastAPIAuthManager
from oidcauthlib.auth.token_reader import TokenReader
from oidcauthlib.auth.well_known_configuration.well_known_configuration_manager import (
    WellKnownConfigurationManager,
)
from oidcauthlib.utilities.environment.abstract_environment_variables import (
    AbstractEnvironmentVariables,
)
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from language_model_gateway.gateway.auth.models.token_cache_item import TokenCacheItem
from language_model_gateway.gateway.auth.token_exchange.token_exchange_manager import (
    TokenExchangeManager,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AUTH"])


class TokenStorageAuthManager(FastAPIAuthManager):
    """
    AuthManager that uses token storage for managing tokens
    """

    def __init__(
        self,
        *,
        environment_variables: AbstractEnvironmentVariables,
        auth_config_reader: AuthConfigReader,
        token_reader: TokenReader,
        token_exchange_manager: TokenExchangeManager,
        well_known_configuration_manager: WellKnownConfigurationManager,
    ) -> None:
        """
        Initialize the TokenStorageAuthManager with required components.
        Args:
            environment_variables (AbstractEnvironmentVariables): Environment variables handler.
            auth_config_reader (AuthConfigReader): Reader for authentication configuration.
            token_reader (TokenReader): Reader for decoding and validating tokens.
            token_exchange_manager (TokenExchangeManager): Manager for token exchange and storage.
        Raises:
            ValueError: If token_exchange_manager is None.
            TypeError: If token_exchange_manager is not an instance of TokenExchangeManager.
        """
        logger.debug(f"Initializing {self.__class__.__name__}")
        super().__init__(
            environment_variables=environment_variables,
            auth_config_reader=auth_config_reader,
            token_reader=token_reader,
            well_known_configuration_manager=well_known_configuration_manager,
        )

        self.token_exchange_manager: TokenExchangeManager = token_exchange_manager
        if self.token_exchange_manager is None:
            raise ValueError("TokenExchangeManager instance is required")
        if not isinstance(self.token_exchange_manager, TokenExchangeManager):
            raise TypeError(
                "token_exchange_manager must be an instance of TokenExchangeManager"
            )

    @override
    async def process_token_async(
        self,
        *,
        code: str | None,
        state_decoded: Dict[str, Any],
        token_dict: dict[str, Any],
        auth_config: AuthConfig,
        url: str | None,
    ) -> Response:
        """
        Process the token received from the OIDC provider.

        This method creates a TokenCacheItem from the token information,
        saves it using the TokenExchangeManager, and returns the token details.
        Args:
            code (str | None): The authorization code received from the OIDC provider.
            state_decoded (Dict[str, Any]): The decoded state information.
            token_dict (dict[str, Any]): The token information as a dictionary.
            auth_config (AuthConfig): The authorization configuration.
            url (str | None): The URL associated with the token.
        Returns:
            Dict[str, Any]: A dictionary containing the token details.
        """
        logger.debug(
            f"Saving token for audience '{auth_config.audience}' and issuer '{auth_config.issuer}': {token_dict=} {state_decoded=}"
        )

        if auth_config.issuer is None:
            raise ValueError("issuer must not be None")

        token_cache_item: TokenCacheItem = (
            self.token_exchange_manager.create_token_cache_item(
                code=code,
                auth_config=auth_config,
                state_decoded=state_decoded,
                token=token_dict,
                url=url,
            )
        )
        content: Dict[str, Any] = token_cache_item.model_dump(mode="json")

        await self.token_exchange_manager.save_token_async(
            token_cache_item=token_cache_item, refreshed=False
        )

        if logger.isEnabledFor(logging.DEBUG):
            access_token: str | None = (
                token_cache_item.access_token.token
                if token_cache_item.access_token
                else None
            )
            access_token_decoded: Dict[str, Any] | None = (
                await self.token_reader.decode_token_async(
                    token=access_token.strip("\n"),
                    verify_signature=False,
                )
                if access_token
                else None
            )
            id_token: str | None = (
                token_cache_item.id_token.token if token_cache_item.id_token else None
            )
            id_token_decoded: Dict[str, Any] | None = (
                await self.token_reader.decode_token_async(
                    token=id_token.strip("\n"),
                    verify_signature=False,
                )
                if id_token
                else None
            )
            refresh_token: str | None = (
                token_cache_item.refresh_token.token
                if token_cache_item.refresh_token
                else None
            )
            refresh_token_decoded: Dict[str, Any] | None = (
                await self.token_reader.decode_token_async(
                    token=refresh_token.strip("\n"),
                    verify_signature=False,
                )
                if refresh_token
                else None
            )
            content["access_token_decoded"] = access_token_decoded
            content["id_token_decoded"] = id_token_decoded
            content["refresh_token_decoded"] = refresh_token_decoded

        return JSONResponse(content)

    @override
    async def process_sign_out_async(
        self,
        *,
        request: Request,
    ) -> None:
        """
        Process sign out by clearing stored tokens.
        """

        # TODO: extract the bearer token from the request and use it to identify the token to be deleted
        pass
