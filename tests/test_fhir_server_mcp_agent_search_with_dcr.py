import asyncio
import logging
import os
from typing import Any
from urllib.parse import urljoin

import httpx
import pytest
from fastmcp import Client
from fastmcp.client import OAuth
from fastmcp.client import StreamableHttpTransport
from httpx import Response, ConnectError

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@pytest.mark.skipif(
    os.environ.get("RUN_TESTS_WITH_REAL_LLM") != "1",
    reason="Environment Variable RUN_TESTS_WITH_REAL_LLM not set",
)
async def test_fhir_server_mcp_agent_search_with_dcr() -> None:
    base_server_url: str | None = "http://localhost:5051/"
    assert base_server_url
    mcp_url: str = base_server_url

    print(f"mcp_url: {mcp_url}")
    logger.info(f"mcp_url: {mcp_url}")

    try:
        async with httpx.AsyncClient() as test_client1_test:
            oauth_authorization_server_url = urljoin(
                mcp_url, ".well-known/oauth-authorization-server"
            )
            test_response: Response = await test_client1_test.get(
                oauth_authorization_server_url
            )
            logger.info(test_response)
            # first try without auth
            my_auth = OAuth(mcp_url=mcp_url)
            # my_auth = OAuthWithoutDynamicRegistration(mcp_url=mcp_url)

            # now create the transport1
            transport1: StreamableHttpTransport = StreamableHttpTransport(
                url=mcp_url, auth=my_auth
            )
            # HTTP server
            client1: Client[Any] = Client(transport=transport1)
            try:
                async with client1:
                    # Basic server interaction
                    await client1.ping()
            except httpx.HTTPStatusError as e:
                logger.info(f"Expected error without auth: {e}")
                assert e.response.status_code == httpx.codes.UNAUTHORIZED
                # extract the WWW-Authenticate header if available
                www_authenticate = e.response.headers.get("WWW-Authenticate")
                # Expected error without auth
                resource_metadata_url = f"{mcp_url}.well-known/oauth-protected-resource"
                expected_www_authenticate = f'Bearer error="invalid_token", error_description="Authentication required", resource_metadata="{resource_metadata_url}"'
                assert www_authenticate == expected_www_authenticate
            except Exception as e:
                logger.info(f"Unexpected error without auth: {e}")
                cause = e.__cause__
                if cause and isinstance(cause, ConnectError):
                    logger.info(f"Cause: {cause}")
                    request = cause.request
                    if request is not None:
                        logger.info(f"Request: {request.method} {request.url}")
                raise e
    except Exception as e:
        logger.error(f"Error in test_fhir_server_mcp_agent_search_with_dcr: {e}")
        raise e


if __name__ == "__main__":
    print("Starting test_fhir_server_mcp_agent_search_with_dcr")
    try:
        asyncio.run(test_fhir_server_mcp_agent_search_with_dcr())
    except Exception as e:
        print(f"Error running test: {e}")
