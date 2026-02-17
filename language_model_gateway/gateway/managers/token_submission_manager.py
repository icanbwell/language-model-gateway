import logging
from fastapi import HTTPException
from oidcauthlib.auth.config.auth_config_reader import AuthConfigReader
from oidcauthlib.auth.token_reader import TokenReader
from starlette.responses import HTMLResponse

from language_model_gateway.gateway.auth.models.token_cache_item import TokenCacheItem
from language_model_gateway.gateway.auth.token_exchange.token_exchange_manager import (
    TokenExchangeManager,
)
from language_model_gateway.gateway.models.token_submission import TokenSubmission
from language_model_gateway.gateway.utilities.auth_success_page import (
    build_auth_success_page,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AUTH"])


class TokenSubmissionManager:
    """Handle manually supplied tokens for downstream use."""

    def __init__(
        self,
        *,
        token_reader: TokenReader,
        token_exchange_manager: TokenExchangeManager,
        auth_config_reader: AuthConfigReader,
    ) -> None:
        if token_reader is None:
            raise ValueError("token_reader must not be None")
        if token_exchange_manager is None:
            raise ValueError("token_exchange_manager must not be None")
        if auth_config_reader is None:
            raise ValueError("auth_config_reader must not be None")
        if not isinstance(token_reader, TokenReader):
            raise TypeError("token_reader must be an instance of TokenReader")
        if not isinstance(token_exchange_manager, TokenExchangeManager):
            raise TypeError(
                "token_exchange_manager must be an instance of TokenExchangeManager"
            )
        if not isinstance(auth_config_reader, AuthConfigReader):
            raise TypeError(
                "auth_config_reader must be an instance of AuthConfigReader"
            )
        self._token_reader = token_reader
        self._token_exchange_manager = token_exchange_manager
        self._auth_config_reader = auth_config_reader

    async def submit_token(
        self,
        *,
        submission: TokenSubmission,
        auth_provider: str,
        referring_email: str,
        referring_subject: str,
    ) -> HTMLResponse:
        if not auth_provider:
            logger.error("Auth provider not specified in token submission")
            raise HTTPException(status_code=400, detail="Auth provider is required")

        auth_config = self._auth_config_reader.get_config_for_auth_provider(
            auth_provider=auth_provider
        )
        if auth_config is None:
            logger.error("Auth config missing for provider '%s'", auth_provider)
            raise HTTPException(status_code=400, detail="Invalid auth provider")

        try:
            verified_token = await self._token_reader.verify_token_async(
                token=submission.token
            )
        except Exception as exc:  # noqa: BLE001 - need to translate any verification issue
            logger.warning(
                "Token verification failed for auth_provider '%s'", auth_provider
            )
            raise HTTPException(
                status_code=400, detail=f"{type(exc)}: Token verification failed: {exc}"
            ) from exc

        if verified_token is None:
            raise HTTPException(status_code=400, detail="Token verification failed")

        token_issuer = getattr(verified_token, "issuer", None)
        if token_issuer and auth_config.issuer and token_issuer != auth_config.issuer:
            logger.error(
                "Token issuer '%s' does not match expected '%s'",
                token_issuer,
                auth_config.issuer,
            )
            raise HTTPException(status_code=400, detail="Token issuer mismatch")

        try:
            token_cache_item = TokenCacheItem.create(
                token=verified_token,
                auth_provider=auth_config.auth_provider.lower(),
                referring_email=referring_email,
                referring_subject=referring_subject,
            )
        except ValueError as exc:
            logger.warning("Unable to build token cache item: %s", exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        token_cache_item.client_id = auth_config.client_id

        await self._token_exchange_manager.delete_token_async(
            referring_subject=referring_subject,
            auth_provider=token_cache_item.auth_provider,
        )
        await self._token_exchange_manager.save_token_async(
            token_cache_item=token_cache_item,
            refreshed=False,
        )

        return build_auth_success_page(submission.token)
