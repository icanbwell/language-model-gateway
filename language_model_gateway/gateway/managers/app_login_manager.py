import logging
from typing import Any

import httpx
from fastapi import HTTPException
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
        referring_email: str,
        referring_subject: str,
    ) -> Response:
        if auth_provider is None:
            logger.error("Auth provider not specified in login request")
            raise HTTPException(status_code=400, detail="Auth provider is required")

        base_url = self._environment_variables.api_gateway_base_url
        client_key = self._environment_variables.app_login_client_key

        if not base_url:
            raise HTTPException(status_code=500, detail="API_GATEWAY_BASE_URL not set")
        if client_key is None:
            raise HTTPException(status_code=500, detail="APP_LOGIN_CLIENT_KEY not set")

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "clientkey": client_key,
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

        auth_config = self.auth_config_reader.get_config_for_auth_provider(
            auth_provider=auth_provider
        )
        if auth_config is None:
            logger.error("No auth config found for auth provider '%s'", auth_provider)
            raise HTTPException(
                status_code=500, detail="Authentication configuration error"
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
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Authentication Successful</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }}
                .container {{ background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); padding: 48px; max-width: 500px; text-align: center; animation: fadeIn 0.5s ease-in; }}
                @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(-20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
                .checkmark {{ width: 80px; height: 80px; border-radius: 50%; display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin-bottom: 24px; position: relative; animation: scaleIn 0.5s ease-in-out; }}
                @keyframes scaleIn {{ from {{ transform: scale(0); }} to {{ transform: scale(1); }} }}
                .checkmark::after {{ content: '✓'; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: white; font-size: 48px; font-weight: bold; }}
                h1 {{ color: #2d3748; font-size: 32px; margin-bottom: 16px; font-weight: 700; }}
                p {{ color: #4a5568; font-size: 18px; line-height: 1.6; margin-bottom: 12px; }}
                .highlight {{ color: #667eea; font-weight: 600; }}
                .footer {{ margin-top: 32px; padding-top: 24px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 14px; }}
                .token-container {{ margin-top: 24px; }}
                .token-label {{ font-weight: 600; color: #2d3748; margin-bottom: 8px; }}
                .token-value {{ display: none; word-break: break-all; background: #f7fafc; border-radius: 8px; padding: 12px; margin-top: 8px; font-size: 15px; color: #4a5568; }}
                .show-btn {{ background: #667eea; color: white; border: none; border-radius: 8px; padding: 8px 16px; cursor: pointer; font-size: 15px; margin-top: 8px; }}
                .show-btn:active {{ background: #764ba2; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="checkmark"></div>
                <h1>Authentication Successful!</h1>
                <p>You have been successfully authenticated.</p>
                <p>You can now go back to <span class="highlight">Aiden</span> and retry your question.</p>
                <div class="token-container">
                    <div class="token-label">Access Token:</div>
                    <button class="show-btn" onclick="toggleToken()">Show Access Token</button>
                    <div id="access-token" class="token-value">{access_token or ""}</div>
                </div>
                <div class="footer">
                    You may close this window.
                </div>
            </div>
            <script>
                function toggleToken() {{
                    var tokenDiv = document.getElementById('access-token');
                    var btn = document.querySelector('.show-btn');
                    if (tokenDiv.style.display === 'none' || tokenDiv.style.display === '') {{
                        tokenDiv.style.display = 'block';
                        btn.textContent = 'Hide Access Token';
                    }} else {{
                        tokenDiv.style.display = 'none';
                        btn.textContent = 'Show Access Token';
                    }}
                }}
            </script>
        </body>
        </html>
        """

        return HTMLResponse(content=html_content)
