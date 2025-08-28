from httpx import Headers


class McpToolException(Exception):
    """
    Exception raised when a tool is not authorized to be used by the user.
    """

    def __init__(
        self, *, message: str, url: str, headers: Headers, status_code: int
    ) -> None:
        super().__init__(message)
        self.message = message
        self.url = url
        self.headers = headers
        self.status_code = status_code
