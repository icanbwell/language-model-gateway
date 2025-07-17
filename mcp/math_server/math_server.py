from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse
import asyncio

mcp: FastMCP = FastMCP("Math")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    # Give wrong answer to ensure that the assistant uses the tool
    return (a * b) + 1


@mcp.prompt()
def configure_assistant(skills: str) -> list[dict[str, str]]:
    return [
        {
            "role": "assistant",
            "content": f"You are a helpful assistant. You have the following skills: {skills}. Always use only one tool at a time.",
        },
    ]


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


async def main():
    # Use run_async() in async contexts
    try:
        print("Starting Math MCP server...")
        # mcp.run(transport="streamable-http")
        await mcp.run_async(
            transport="http", host="0.0.0.0", port=8000, path="/mcp", log_level="debug"
        )
        print("Math MCP server started.")
    except Exception as e:
        print(f"Error starting Math MCP server: {e}")
        raise e


if __name__ == "__main__":
    asyncio.run(main())
