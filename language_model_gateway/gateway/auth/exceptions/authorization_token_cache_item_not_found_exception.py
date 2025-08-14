from language_model_gateway.gateway.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)


class AuthorizationTokenCacheItemNotFoundException(AuthorizationNeededException):
    """
    Exception raised when authorization is needed for a specific operation.
    This exception is used to indicate that the user needs to authenticate
    or provide valid credentials before proceeding with the operation.
    """

    def __init__(self, *, message: str, tool_auth_audiences: list[str] | None) -> None:
        """
        Initialize the AuthorizationNeededException with a message and an optional token cache item.
        """
        super().__init__(message=message)
        self.message = message
        self.tool_auth_audiences = tool_auth_audiences
