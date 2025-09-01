from language_model_gateway.gateway.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)


class AuthorizationTokenCacheItemNotFoundException(AuthorizationNeededException):
    """
    Exception raised when a token cache item is not found.
    This exception is used to indicate that the requested token cache item does not exist
    in the cache, which may occur if the token has never been cached or has been removed
    due to expiration or other reasons.
    It inherits from AuthorizationNeededException and provides a message to indicate the
    nature of the error, along with an optional list of tool authentication audiences
    that may be relevant for the authorization process.
    """

    def __init__(self, *, message: str, tool_auth_providers: list[str] | None) -> None:
        """
        Initialize the AuthorizationNeededException with a message and an optional token cache item.
        """
        super().__init__(message=message)
        self.message = message
        self.tool_auth_providers = tool_auth_providers
