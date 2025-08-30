from language_model_gateway.gateway.mcp.exceptions.mcp_tool_exception import (
    McpToolException,
)


class McpToolUnauthorizedException(McpToolException):
    """
    Exception raised when a tool is not authorized to be used by the user.
    """

    pass
