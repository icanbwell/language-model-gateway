from language_model_gateway.gateway.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)


class AuthorizationBearerTokenMissingException(AuthorizationNeededException):
    """
    Exception raised when a bearer token is missing.
    This exception is used to indicate that the required bearer token is not present
    in the request headers or parameters, and therefore authorization cannot be performed.
    It inherits from AuthorizationNeededException and provides a message to indicate the
    nature of the error.
    """

    def __init__(self, *, message: str) -> None:
        """
        Initialize the AuthorizationNeededException with a message and an optional token cache item.
        """
        super().__init__(message=message)
        self.message = message
