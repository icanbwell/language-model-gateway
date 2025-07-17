from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")


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


if __name__ == "__main__":
    mcp.run(transport="stdio")
