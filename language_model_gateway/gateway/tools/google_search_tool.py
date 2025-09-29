import asyncio
import logging
import os
import random
from os import environ
from typing import Optional, Dict, Any, List, cast, Type, Literal, Tuple

import httpx
from pydantic import PrivateAttr, Field, BaseModel

from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__file__)
logger.setLevel(SRC_LOG_LEVELS["AGENTS"])


# Utility to redact sensitive info from params
def redact_params(params: Dict[str, Any]) -> Dict[str, Any]:
    redacted = params.copy()
    for sensitive_key in ("key", "cx", "api_key", "cse_id"):
        if sensitive_key in redacted:
            redacted[sensitive_key] = "***REDACTED***"
    return redacted


class GoogleSearchToolInput(BaseModel):
    query: str = Field(description="The search query to send to Google Search")
    use_verbose_logging: Optional[bool] = Field(
        default=False,
        description="Whether to enable verbose logging",
    )


class GoogleSearchTool(ResilientBaseTool):
    """
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

    """

    name: str = "google_search"
    description: str = "Search Google for recent results."

    args_schema: Type[BaseModel] = GoogleSearchToolInput
    response_format: Literal["content", "content_and_artifact"] = "content_and_artifact"

    # Private attributes
    _client: httpx.AsyncClient = PrivateAttr()
    _api_key: Optional[str] = PrivateAttr()
    _cse_id: Optional[str] = PrivateAttr()
    _max_retries: int = PrivateAttr(default=3)
    _base_delay: float = PrivateAttr(default=1.0)
    _max_delay: float = PrivateAttr(default=60.0)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._client = httpx.AsyncClient()
        api_key: Optional[str] = environ.get("GOOGLE_API_KEY")
        cse_id: Optional[str] = environ.get("GOOGLE_CSE_ID")
        self._api_key = api_key
        self._cse_id = cse_id

    async def _handle_rate_limit(self, *, retry_count: int, error_text: str) -> None:
        """Handle rate limiting with exponential backoff."""
        if retry_count >= self._max_retries:
            raise Exception(f"Max retries exceeded for Google Search API: {error_text}")

        delay = min(self._base_delay * (2**retry_count), self._max_delay)
        jitter = delay * 0.1 * (2 * random.random() - 1)  # Add 10% jitter
        total_delay = delay + jitter

        logger.warning(f"Rate limit hit. Retrying in {total_delay:.2f} seconds...")
        await asyncio.sleep(total_delay)

    async def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request with retry logic for rate limiting."""
        retry_count = 0

        while True:
            try:
                if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1":
                    safe_params = redact_params(params)
                    logger.info(
                        f"Running Google search with query {params.get('q')}. Params: {safe_params}. Retry count: {retry_count}"
                    )

                response = await self._client.get(url, params=params)

                if response.status_code == 429:  # Too Many Requests
                    text = response.text
                    await self._handle_rate_limit(
                        retry_count=retry_count, error_text=text
                    )
                    retry_count += 1
                    continue

                response.raise_for_status()
                response_json = response.json()
                assert isinstance(response_json, dict)
                return cast(Dict[str, Any], response_json)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    text = e.response.text
                    await self._handle_rate_limit(
                        retry_count=retry_count, error_text=text
                    )
                    retry_count += 1
                    continue
                raise
            except Exception as e:
                safe_params = redact_params(params)
                logger.exception(
                    f"Error making request for {url} with params {safe_params}\n{str(e)}"
                )
                raise

    async def aclose(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    def _run(
        self, query: str, use_verbose_logging: Optional[bool] = None
    ) -> Tuple[str, str]:
        """Use async version of this tool."""
        raise NotImplementedError("Use async version of this tool")

    async def _arun(
        self, query: str, use_verbose_logging: Optional[bool] = None
    ) -> Tuple[str, str]:
        """Async implementation of the Google search tool."""

        assert self._api_key, "GOOGLE_API_KEY environment variable is required"
        assert self._cse_id, "GOOGLE_CSE_ID environment variable is required"

        snippets: List[str] = []
        try:
            # Result follows https://developers.google.com/custom-search/v1/reference/rest/v1/Search
            results: List[Dict[str, Any]] = await self._search_async(
                q=query,
                c2coff="1",
                num=10,
            )
            if len(results) == 0:
                return (
                    "No good Google Search Result was found",
                    f'GoogleSearchAgent: Searched Google for "{query}"',
                )

            for result in results:
                if "snippet" in result:
                    snippets.append(f"- {result['snippet']} ({result.get('link')})")

            response: str = "\n".join(snippets)
            if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1":
                logger.info(f"Google Search results: {response}")

            artifact: str = f'GoogleSearchAgent: Searched Google for "{query}"'
            if use_verbose_logging:
                artifact += f"\n```{response}```"
            return response, artifact
        except Exception as e:
            logger.exception(e, stack_info=True)
            return (
                "Ran into an error while running Google Search",
                f'GoogleSearchAgent: Searched Google for "{query}"',
            )

    # noinspection PyPep8Naming,PyShadowingBuiltins
    async def _search_async(
        self,
        q: str,
        c2coff: Optional[str] = None,
        cr: Optional[str] = None,
        dateRestrict: Optional[str] = None,
        exactTerms: Optional[str] = None,
        excludeTerms: Optional[str] = None,
        fileType: Optional[str] = None,
        filter: Optional[str] = None,
        gl: Optional[str] = None,
        googleHost: Optional[str] = None,
        highRange: Optional[str] = None,
        hl: Optional[str] = None,
        hq: Optional[str] = None,
        imgColorType: Optional[str] = None,
        imgDominantColor: Optional[str] = None,
        imgSize: Optional[str] = None,
        imgType: Optional[str] = None,
        linkSite: Optional[str] = None,
        lowRange: Optional[str] = None,
        lr: Optional[str] = None,
        num: Optional[int] = None,
        orTerms: Optional[str] = None,
        rights: Optional[str] = None,
        safe: Optional[str] = None,
        searchType: Optional[str] = None,
        siteSearch: Optional[str] = None,
        siteSearchFilter: Optional[str] = None,
        sort: Optional[str] = None,
        start: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Execute the Google search query."""
        params = {"key": self._api_key, "cx": self._cse_id, "q": q}

        # Add optional parameters if they are provided
        optional_params = locals()
        for param, value in optional_params.items():
            if param not in ["self", "q"] and value is not None:
                params[param] = value

        url: str = "https://customsearch.googleapis.com/customsearch/v1"
        # parameters follow https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list
        try:
            result = await self._make_request(url, params)
            if not result:
                safe_params = redact_params(params)
                logger.exception(
                    f"Error making request for {url} with params {safe_params}"
                )
                raise Exception(
                    f"Error making request for {url} with params {safe_params}"
                )

            # Result follows https://developers.google.com/custom-search/v1/reference/rest/v1/Search
            return cast(List[Dict[str, Any]], result.get("items", []))
        except Exception as e:
            logger.exception(f"Error in Google Search: {str(e)}")
            raise
