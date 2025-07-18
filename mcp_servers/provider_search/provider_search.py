import asyncio
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

# Example doctor database
DOCTOR_DB = {
    "Dr. Alice Smith": "123 Main St, Springfield",
    "Dr. Bob Jones": "456 Elm St, Shelbyville",
    "Dr. Carol White": "789 Oak St, Capital City",
}

mcp: FastMCP = FastMCP("ProviderSearch")


@mcp.tool()
def get_doctor_address(doctor_name: str) -> str:
    """Return the address of the doctor given their name."""
    return DOCTOR_DB.get(doctor_name, "Doctor not found.")


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


async def main():
    try:
        print("Starting Provider Search MCP server...")
        await mcp.run_async(
            transport="http",
            host="0.0.0.0",
            port=8001,
            path="/mcp",
            log_level="debug",  # nosec B104
        )
        print("Provider Search MCP server started.")
    except Exception as e:
        print(f"Error starting Provider Search MCP server: {e}")
        raise e


if __name__ == "__main__":
    asyncio.run(main())
