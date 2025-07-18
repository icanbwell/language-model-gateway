from typing import Any, Dict

from fastmcp import FastMCP, Context
from fastmcp.server.dependencies import get_http_request
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import PlainTextResponse
import os
import httpx
import asyncio

mcp: FastMCP = FastMCP("GoogleSearch")

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID")


async def google_search(query: str, headers: Headers) -> Dict[str, Any]:
    """
    Perform a Google search using the Custom Search API.

    2. Enable the Custom Search API
    - Navigate to the APIs & Services→Dashboard panel in Cloud Console.
    - Click Enable APIs and Services.
    - Search for Custom Search API and click on it.
    - Click Enable.
    URL for it: https://console.cloud.google.com/apis/library/customsearch.googleapis
    .com

    3. To create an API key:
    - Navigate to the APIs & Services → Credentials panel in Cloud Console.
    - Select Create credentials, then select API key from the drop-down menu.
    - The API key created dialog box displays your newly created key.
    - You now have an API_KEY

    Alternatively, you can just generate an API key here:
    https://developers.google.com/custom-search/docs/paid_element#api_key

    4. Setup Custom Search Engine so you can search the entire web
    - Create a custom search engine here: https://programmablesearchengine.google.com/.
    - In `What to search` to search, pick the `Search the entire Web` option.
    After search engine is created, you can click on it and find `Search engine ID`
      on the Overview page.

    Args:
        query (str): The search query to perform.
        headers (Headers): The headers from the request, which may contain API keys.
    Returns:
        dict: The search results from Google Custom Search API.
    """
    url = "https://www.googleapis.com/customsearch/v1"

    google_api_key = headers.get("GOOGLE_API_KEY", GOOGLE_API_KEY)
    google_cse_id = headers.get("GOOGLE_CSE_ID", GOOGLE_CSE_ID)

    assert google_api_key, "GOOGLE_API_KEY environment variable is required"
    assert google_cse_id, "GOOGLE_CSE_ID environment variable is required"
    params = {
        "key": google_api_key,
        "cx": google_cse_id,
        "q": query,
    }

    print(f"Running Google search with query: {query}. Params: {params}")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            return {
                "error": "HTTP error occurred",
                "status_code": e.response.status_code,
                "message": str(e),
            }


@mcp.tool()
async def search_google(query: str, ctx: Context) -> dict:
    """Search Google for recent results using the Custom Search API.
    Args:
        query (str): The search query to perform.
        ctx (Context): The context for the MCP request. https://github.com/jlowin/fastmcp/blob/main/src/fastmcp/server/context.py
    Returns:
        dict: The search results from Google Custom Search API.
    """
    # Get the HTTP request
    request: Request = get_http_request()

    headers: Headers = request.headers
    return await google_search(query, headers)


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
        print("Starting Google Search MCP server...")
        await mcp.run_async(
            transport="http",
            host="0.0.0.0",
            port=8002,
            path="/mcp",
            log_level="debug",
        )
    except Exception as e:
        print(f"Error running server: {e}")


if __name__ == "__main__":
    asyncio.run(main())
