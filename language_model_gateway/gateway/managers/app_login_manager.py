import logging
from typing import Any

import httpx
from fastapi import HTTPException
from oidcauthlib.auth.config.auth_config import AuthConfig
from oidcauthlib.auth.config.auth_config_reader import AuthConfigReader
from starlette.responses import HTMLResponse, Response

from language_model_gateway.gateway.auth.models.token_cache_item import TokenCacheItem
from language_model_gateway.gateway.auth.token_exchange.token_exchange_manager import (
    TokenExchangeManager,
)
from language_model_gateway.gateway.http.http_client_factory import HttpClientFactory
from language_model_gateway.gateway.models.app_login_submission import (
    CredentialSubmission,
)
from language_model_gateway.gateway.utilities.auth_success_page import (
    build_auth_success_page,
)
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AUTH"])


class AppLoginManager:
    """Handle credential submissions for app logins."""

    def __init__(
        self,
        *,
        http_client_factory: HttpClientFactory,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
        token_exchange_manager: TokenExchangeManager,
        auth_config_reader: AuthConfigReader,
    ) -> None:
        self._http_client_factory = http_client_factory
        if self._http_client_factory is None:
            raise ValueError("http_client_factory must not be None")
        if not isinstance(self._http_client_factory, HttpClientFactory):
            raise TypeError(
                "http_client_factory must be an instance of HttpClientFactory"
            )
        self._environment_variables = environment_variables
        if self._environment_variables is None:
            raise ValueError("environment_variables must not be None")
        if not isinstance(
            self._environment_variables, LanguageModelGatewayEnvironmentVariables
        ):
            raise TypeError(
                "environment_variables must be an instance of LanguageModelGatewayEnvironmentVariables"
            )
        self.token_exchange_manager = token_exchange_manager
        if self.token_exchange_manager is None:
            raise ValueError("token_exchange_manager must not be None")
        if not isinstance(self.token_exchange_manager, TokenExchangeManager):
            raise TypeError(
                "token_exchange_manager must be an instance of TokenExchangeManager"
            )

        self.auth_config_reader = auth_config_reader
        if self.auth_config_reader is None:
            raise ValueError("auth_config_reader must not be None")
        if not isinstance(self.auth_config_reader, AuthConfigReader):
            raise TypeError(
                "auth_config_reader must be an instance of AuthConfigReader"
            )

    async def login(
        self,
        *,
        submission: CredentialSubmission,
        auth_provider: str,
        auth_client_key: str,
        referring_email: str,
        referring_subject: str,
    ) -> Response:
        if auth_provider is None:
            logger.error("Auth provider not specified in login request")
            raise HTTPException(status_code=400, detail="Auth provider is required")

        auth_config: AuthConfig | None = (
            self.auth_config_reader.get_config_for_auth_provider(
                auth_provider=auth_provider
            )
        )
        if auth_config is None:
            logger.error("No auth config found for auth provider '%s'", auth_provider)
            raise HTTPException(
                status_code=500, detail="Authentication configuration error"
            )

        auth_config_extra_info: dict[str, str] | None = auth_config.extra_info
        base_url = (
            auth_config_extra_info.get("api_gateway_base_url")
            if auth_config_extra_info
            else None
        )

        if not base_url:
            logger.error(
                f"api_gateway_base_url not set in auth config extra_info for auth provider '{auth_provider}'"
            )
            raise HTTPException(
                status_code=500,
                detail=f"api_gateway_base_url not set in auth config extra_info for auth provider '{auth_provider}'",
            )

        if auth_client_key is None:
            raise HTTPException(status_code=500, detail="auth_client_key not set")

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "clientkey": auth_client_key,
        }

        try:
            async with self._http_client_factory.create_http_client(
                base_url=base_url,
                headers=headers,
            ) as client:
                response = await client.post(
                    "/identity/account/login",
                    json={
                        "email": submission.username,
                        "password": submission.password,
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "App login failed with HTTP status %s", exc.response.status_code
            )
            raise HTTPException(
                status_code=exc.response.status_code,
                detail="Login request failed",
            ) from exc
        except httpx.HTTPError as exc:
            logger.exception("App login request could not be completed")
            raise HTTPException(
                status_code=502, detail="Unable to reach login service"
            ) from exc

        payload: dict[str, Any]
        try:
            payload = response.json()
        except ValueError as exc:
            logger.exception("Login service returned invalid JSON")
            raise HTTPException(
                status_code=502, detail="Invalid response from login service"
            ) from exc

        access_token_from_payload = payload.get("accessToken", {}).get("jwtToken")
        if not access_token_from_payload:
            logger.warning("Login service response did not include access token")
            raise HTTPException(
                status_code=502, detail="Access token missing in login response"
            )

        token_dict: dict[str, Any] = {
            "access_token": access_token_from_payload,
            "id_token": payload.get("idToken", {}).get("jwtToken"),
            "refresh_token": payload.get("refreshToken", {}).get("token"),
        }
        token_cache_item: TokenCacheItem = (
            self.token_exchange_manager.create_token_cache_item(
                code=None,
                auth_config=auth_config,
                state_decoded={
                    "referring_email": referring_email,
                    "referring_subject": referring_subject,
                },
                token=token_dict,
                url=None,
            )
        )
        # content: dict[str, Any] = token_cache_item.model_dump(mode="json")

        # delete any existing tokens with same referring_subject and auth_provider
        await self.token_exchange_manager.delete_token_async(
            referring_subject=token_cache_item.referring_subject,
            auth_provider=token_cache_item.auth_provider,
        )

        await self.token_exchange_manager.save_token_async(
            token_cache_item=token_cache_item, refreshed=False
        )
        # return JSONResponse({"accessToken": access_token_from_payload})
        return await self.get_html_response(token_dict.get("access_token"))

    async def get_html_response(self, access_token: str | None) -> HTMLResponse:
        return build_auth_success_page(access_token)

    async def get_client_keys_for_auth_provider(
        self, auth_provider: str
    ) -> dict[str, str] | None:
        auth_config: AuthConfig | None = (
            self.auth_config_reader.get_config_for_auth_provider(
                auth_provider=auth_provider
            )
        )
        if auth_config is None:
            logger.error("No auth config found for auth provider '%s'", auth_provider)
            raise HTTPException(
                status_code=500, detail="Authentication configuration error"
            )

        auth_config_extra_info: dict[str, Any] | None = auth_config.extra_info
        client_keys: dict[str, str] | None = (
            auth_config_extra_info.get("client_keys")
            if auth_config_extra_info
            else None
        )
        if not client_keys:
            logger.error(
                f"client_keys not set in auth config extra_info for auth provider '{auth_provider}'"
            )
            raise HTTPException(
                status_code=500,
                detail=f"client_keys not set in auth config extra_info for auth provider '{auth_provider}'",
            )

        return client_keys
