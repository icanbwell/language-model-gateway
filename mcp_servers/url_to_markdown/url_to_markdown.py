import asyncio

import httpx
from fastmcp import FastMCP
from httpx import Headers
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from html_to_markdown_converter import HtmlToMarkdownConverter

mcp: FastMCP = FastMCP("URLToMarkdown")


@mcp.tool()
async def url_to_markdown_tool(url: str) -> str:
    """Fetches the content of a webpage from a given URL and converts it to Markdown format."""
    try:
        headers = Headers(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/pdf, text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            html_content = response.text

        content: str = await HtmlToMarkdownConverter.get_markdown_from_html_async(
            html_content=html_content
        )

        # artifact: str = f"URLToMarkdownAgent: Scraped content from <{url}> "

        return content
    except Exception as e:
        return f"Failed to fetch or process the URL {url}: {str(e)}"


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
    try:
        print("Starting URL to Markdown MCP server...")
        await mcp.run_async(
            transport="http",
            host="0.0.0.0",
            port=8003,
            path="/mcp",
            log_level="debug",
        )
    except Exception as e:
        print(f"Error running server: {e}")


if __name__ == "__main__":
    asyncio.run(main())
