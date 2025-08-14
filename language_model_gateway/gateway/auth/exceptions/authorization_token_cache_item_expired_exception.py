from language_model_gateway.gateway.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)
from language_model_gateway.gateway.auth.models.token_cache_item import TokenCacheItem


class AuthorizationTokenCacheItemExpiredException(AuthorizationNeededException):
    """
    Exception raised when authorization is needed for a specific operation.
    This exception is used to indicate that the user needs to authenticate
    or provide valid credentials before proceeding with the operation.
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
