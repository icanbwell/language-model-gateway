class AuthorizationNeededException(Exception):
    """
    Exception raised when authorization is needed to access a resource or perform an action.
    This exception is used to indicate that the current request does not have the necessary
    authorization credentials, such as a valid token, to proceed.
    It can be used in various authentication and authorization scenarios where a user or
    system must provide valid credentials to access protected resources or perform specific actions.
    It inherits from the built-in Exception class and provides a message to indicate the
    nature of the authorization requirement.
    """

    def __init__(self, *, message: str) -> None:
        """
        Initialize the AuthorizationNeededException with a message and an optional token cache item.
        """
        super().__init__(message)
        self.message = message
