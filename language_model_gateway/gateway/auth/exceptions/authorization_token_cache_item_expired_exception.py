from language_model_gateway.gateway.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)
from language_model_gateway.gateway.auth.models.token_cache_item import TokenCacheItem


class AuthorizationTokenCacheItemExpiredException(AuthorizationNeededException):
    """
    Exception raised when a token cache item has expired.
    This exception is used to indicate that the cached token is no longer valid
    and needs to be refreshed or re-obtained.
    It inherits from AuthorizationNeededException and provides a message to indicate the
    nature of the error, along with an optional token cache item for further context.
    """

    def __init__(
        self, *, message: str, token_cache_item: TokenCacheItem | None
    ) -> None:
        """
        Initialize the AuthorizationNeededException with a message and an optional token cache item.
        """
        super().__init__(message=message)
        self.message = message
        self.token_cache_item: TokenCacheItem | None = token_cache_item
