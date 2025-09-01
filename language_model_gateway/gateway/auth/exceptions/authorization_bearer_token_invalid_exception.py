from language_model_gateway.gateway.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)


class AuthorizationBearerTokenInvalidException(AuthorizationNeededException):
    """
    Exception raised when a bearer token is invalid.
    This exception is used to indicate that the provided token does not meet the
    required format or is not recognized by the authentication system.
    It inherits from AuthorizationNeededException and provides additional context
    about the invalid token.
    """

    def __init__(self, *, message: str, token: str) -> None:
        """
        Initialize the AuthorizationNeededException with a message and an optional token cache item.
        """
        super().__init__(message=message)
        self.message = message
        self.token: str = token
