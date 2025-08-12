class AuthorizationNeededException(Exception):
    """
    Exception raised when authorization is needed for a specific operation.
    This exception is used to indicate that the user needs to authenticate
    or provide valid credentials before proceeding with the operation.
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
