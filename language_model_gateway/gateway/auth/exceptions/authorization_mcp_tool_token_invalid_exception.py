from language_model_gateway.gateway.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)
from language_model_gateway.gateway.auth.models.token import Token


class AuthorizationMcpToolTokenInvalidException(AuthorizationNeededException):
    """
    Exception raised when a tool token is invalid.
    This exception is used to indicate that the provided tool token does not meet the
    required format or is not recognized by the authentication system.
    It inherits from AuthorizationNeededException and provides additional context
    about the invalid token and the tool URL.
    """

    def __init__(self, *, message: str, token: Token | None, tool_url: str) -> None:
        """
        Initialize the AuthorizationNeededException with a message and an optional token cache item.
        """
        super().__init__(message=message)
        self.message = message
        self.token: Token | None = token
        self.tool_url: str = tool_url
