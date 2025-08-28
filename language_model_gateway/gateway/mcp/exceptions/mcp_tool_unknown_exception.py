from language_model_gateway.gateway.mcp.exceptions.mcp_tool_exception import (
    McpToolException,
)


class McpToolUnknownException(McpToolException):
    """
    Exception raised when a tool encounters an unknown error.
    """

    pass
