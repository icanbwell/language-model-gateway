from language_model_gateway.gateway.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)


class AuthorizationBearerTokenExpiredException(AuthorizationNeededException):
    """
    Exception raised when a bearer token has expired and needs to be refreshed.
    This exception is used to indicate that the current token is no longer valid and
    a new token must be obtained to continue the operation.
    It inherits from AuthorizationNeededException and provides additional context
    about the expired token, including its expiration time and the current time.
    It also includes the issuer and audience of the token, if available.
    This exception is typically raised in scenarios where a token is required for
    authentication or authorization, and the existing token has expired.
    """

    def __init__(
        self,
        *,
        message: str,
        token: str,
        expires: str,
        now: str,
        issuer: str | None,
        audience: str | None,
    ) -> None:
        """
        Initialize the AuthorizationNeededException with a message and an optional token cache item.
        """
        super().__init__(message=message)
        self.message = message
        self.token: str = token
        self.expires: str = expires
        self.now: str = now
        self.issuer: str | None = issuer
        self.audience: str | None = audience
