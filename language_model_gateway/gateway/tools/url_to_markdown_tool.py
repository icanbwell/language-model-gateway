import logging
import os
from typing import Type, Literal, Tuple, Optional

import httpx
from httpx import Headers
from pydantic import BaseModel, Field

from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool
from language_model_gateway.gateway.utilities.html_to_markdown_converter import (
    HtmlToMarkdownConverter,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AGENTS"])


class URLToMarkdownToolInput(BaseModel):
    url: str = Field(description="url of the webpage to scrape")
    use_verbose_logging: Optional[bool] = Field(
        default=False,
        description="Whether to enable verbose logging",
    )


class URLToMarkdownTool(ResilientBaseTool):
    """
    LangChain-compatible tool for downloading the content of a URL and converting it to Markdown.
    """

    name: str = "url_to_markdown"
    description: str = (
        "Fetches the content of a webpage from a given URL and converts it to Markdown format. "
        "Provide the URL as input. The tool will return the main content of the page formatted as Markdown."
    )
    args_schema: Type[BaseModel] = URLToMarkdownToolInput
    response_format: Literal["content", "content_and_artifact"] = "content_and_artifact"

    def _run(
        self, url: str, use_verbose_logging: Optional[bool] = None
    ) -> Tuple[str, str]:
        """
        Synchronous version of the tool (falls back to async implementation).
        :param url: The URL of the webpage to fetch.
        :return: The content of the webpage in Markdown format.
        """
        raise NotImplementedError("Use async version of this tool")

    async def _arun(
        self, url: str, use_verbose_logging: Optional[bool] = None
    ) -> Tuple[str, str]:
        """
        Asynchronous version of the tool.
        :param url: The URL of the webpage to fetch.
        :return: The content of the webpage in Markdown format.
        """
        logger.info(f"Fetching and converting URL to Markdown: {url}")
        try:
            headers = Headers(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "application/pdf, text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                }
            )
            async with httpx.AsyncClient(
                headers=headers, follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                html_content = response.text

            content: str = await HtmlToMarkdownConverter.get_markdown_from_html_async(
                html_content=html_content
            )
            if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1":
                logger.info(
                    f"====== Scraped {url} ======\n{content}\n====== End of Scraped Markdown ======"
                )
            artifact: str = f"URLToMarkdownAgent: Scraped content from <{url}> "
            if use_verbose_logging:
                logger.info(f"\n```\n{content}\n```")
            return content, artifact
        except Exception as e:
            return (
                f"Failed to fetch or process the URL {url}: {str(e)}",
                f"URLToMarkdownAgent: Failed to fetch or process the URL: <{url}> ",
            )
