from httpx import Headers


class McpToolException(Exception):
    """
    Exception raised when a tool is not authorized to be used by the user.
    """

    def __init__(
        self,
        *,
        message: str,
        url: str,
        headers: Headers | None,
        status_code: int | None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.url: str = url
        self.headers: Headers | None = headers
        self.status_code: int | None = status_code
