"""title: LangChain Pipe Function (Streaming Version)
author: Imran Qureshi @ b.well Connected Health (mailto:imran.qureshi@bwell.com)
author_url: https://github.com/imranq2
version: 0.2.0
This module defines a Pipe class that reads the oauth_id_token from the request cookies and uses it in Authorization header
to make requests to the OpenAI API. It supports both streaming and non-streaming responses.
"""

import asyncio
import datetime
import json
import logging
import os
import time
from pathlib import PurePosixPath
from typing import AsyncGenerator, List
from typing import Optional, Callable, Awaitable, Any, Dict
from urllib.parse import urlparse, urlunparse

import httpx
from pydantic import BaseModel
from pydantic import Field
from starlette.requests import Request

logger = logging.getLogger(__name__)


class Pipe:
    class Valves(BaseModel):
        emit_interval: float = Field(
            default=2.0, description="Interval in seconds between status emissions"
        )
        enable_status_indicator: bool = Field(
            default=True, description="Enable or disable status indicator emissions"
        )
        OPENAI_API_BASE_URL: str | None = Field(
            default=None,
            description="Base URL for OpenAI API, e.g., https://api.openai.com/v1",
        )
        model_name_prefix: str = Field(
            default="MCP: ",
            description="Prefix for model names in the dropdown",
        )
        restrict_to_admins: bool = Field(
            default=False,
            description="Restrict access to this pipe to admin users only",
        )
        restrict_to_model_ids: list[str] = Field(
            default_factory=list,
            description="List of model IDs to restrict access to. If empty, no restriction is applied.",
        )
        debug_mode: bool = Field(
            default=False,
            description="Enable debug mode for additional logging and debugging information",
        )

    def __init__(self) -> None:
        self.type: str = "pipe"
        self.id: str = "language_model_gateway"
        openai_api_base_url_ = self.read_base_url()
        self.valves = self.Valves(OPENAI_API_BASE_URL=openai_api_base_url_)
        self.name: str = self.valves.model_name_prefix
        self.last_emit_time: float = 0
        self.pipelines: List[Dict[str, Any]] | None = None

    # noinspection PyMethodMayBeStatic
    def read_base_url(self) -> Optional[str]:
        """
        Reads the OpenAI API base URL from environment variables.
        Returns:
            The OpenAI API base URL if set, otherwise None.
        """
        return os.getenv("LANGUAGE_MODEL_GATEWAY_API_BASE_URL") or os.getenv(
            "OPENAI_API_BASE_URL"
        )

    # noinspection PyMethodMayBeStatic
    async def on_startup(self) -> None:
        # This function is called when the server is started.
        logger.debug(f"on_startup:{__name__}")
        self.pipelines = await self.get_models()
        pass

    # noinspection PyMethodMayBeStatic
    async def on_shutdown(self) -> None:
        # This function is called when the server is stopped.
        logger.debug(f"on_shutdown:{__name__}")
        pass

    async def on_valves_updated(self) -> None:
        # This function is called when the valves are updated.
        logger.debug(f"on_valves_updated:{__name__}")
        self.pipelines = await self.get_models()
        pass

    async def emit_status(
        self,
        __event_emitter__: Optional[Callable[[Dict[str, Any]], Awaitable[None]]],
        level: str,
        message: str,
        done: bool,
    ) -> None:
        current_time = time.time()
        if (
            __event_emitter__
            and self.valves.enable_status_indicator
            and (
                current_time - self.last_emit_time >= self.valves.emit_interval or done
            )
        ):
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "status": "complete" if done else "in_progress",
                        "level": level,
                        "description": message,
                        "done": done,
                    },
                }
            )
            self.last_emit_time = current_time

    async def stream_hardcoded_response(
        self,
        *,
        body: Dict[str, Any],
        __request__: Optional[Request] = None,
        __user__: Optional[Dict[str, Any]] = None,
        __event_emitter__: Callable[[Dict[str, Any]], Awaitable[None]] | None = None,
        __event_call__: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
        | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Async generator to stream response chunks
        """
        try:
            await self.emit_status(
                __event_emitter__,
                "info",
                f"/initiating Chain: headers={__request__.headers if __request__ else None}"
                f", cookies={__request__.cookies if __request__ else None}"
                f" {__user__=} {body=}",
                False,
            )

            if __request__ is None or __user__ is None:
                raise ValueError("Request and user information must be provided.")

            # Simulate streaming response
            # Generate chunks in OpenAI streaming format
            chunks = [
                {
                    "id": "chatcmpl-123",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "gpt-3.5-turbo",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None,
                        }
                    ],
                },
                {
                    "id": "chatcmpl-123",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "gpt-3.5-turbo",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": "Here"},
                            "finish_reason": None,
                        }
                    ],
                },
                {
                    "id": "chatcmpl-123",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "gpt-3.5-turbo",
                    "choices": [
                        {"index": 0, "delta": {"content": " is"}, "finish_reason": None}
                    ],
                },
                {
                    "id": "chatcmpl-123",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "gpt-3.5-turbo",
                    "choices": [
                        {"index": 0, "delta": {"content": " a"}, "finish_reason": None}
                    ],
                },
                {
                    "id": "chatcmpl-123",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "gpt-3.5-turbo",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": " streamed"},
                            "finish_reason": None,
                        }
                    ],
                },
                {
                    "id": "chatcmpl-123",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "gpt-3.5-turbo",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "content": f"\nheaders=\n{__request__.headers}\ncookies=\n{__request__.cookies}\n{__user__=}\n{body=}",
                            },
                            "finish_reason": None,
                        }
                    ],
                },
                {
                    "id": "chatcmpl-123",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "gpt-3.5-turbo",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "content": f"\nOAuth_id_token:\n{__request__.cookies.get('oauth_id_token')}\n",
                            },
                            "finish_reason": None,
                        }
                    ],
                },
                {
                    "id": "chatcmpl-123",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "gpt-3.5-turbo",
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                },
            ]

            for chunk in chunks:
                # Yield each chunk as a JSON-encoded string with a data: prefix
                yield f"data: {json.dumps(chunk)}\n\n"
                await self.emit_status(__event_emitter__, "info", "Streaming...", False)
                await asyncio.sleep(0.5)  # Simulate streaming delay

            await self.emit_status(__event_emitter__, "info", "Stream Complete", True)

        except Exception as e:
            error_chunk = {
                "id": "chatcmpl-error",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "error",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": f"Error: {str(e)}"},
                        "finish_reason": "stop",
                    }
                ],
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            await self.emit_status(__event_emitter__, "error", str(e), True)

    @classmethod
    def pathlib_url_join(cls, base_url: str, path: str) -> str:
        """
        Join URLs using pathlib for path manipulation.

        Args:
            base_url: The base URL
            path: Path to append

        Returns:
            Fully constructed URL
        """
        # Parse the base URL
        parsed_base = urlparse(base_url)

        # Use PurePosixPath to handle path joining
        full_path = str(PurePosixPath(parsed_base.path) / path.lstrip("/"))

        # Reconstruct the URL
        reconstructed_url = urlunparse(
            (
                parsed_base.scheme,
                parsed_base.netloc,
                full_path,
                parsed_base.params,
                parsed_base.query,
                parsed_base.fragment,
            )
        )

        return reconstructed_url

    @staticmethod
    def log_httpx_request(request: httpx.Request) -> str:
        """
        Convert an HTTPX request to a detailed string representation.

        Args:
            request (httpx.Request): The HTTPX request to log

        Returns:
            str: Formatted string representation of the request
        """
        # Construct request details
        request_log = f"""
    HTTPX Request:
    - Method: {request.method}
    - URL: {request.url}
    - Headers: {dict(request.headers)}
    - Body: {request.content.decode("utf-8", errors="replace") if request.content else "No body"}
    """.strip()

        return request_log

    @staticmethod
    def log_response_as_string(response1: httpx.Response) -> str:
        """
        Convert an HTTPX response to a detailed, formatted string.

        Args:
            response1 (httpx.Response): The HTTP response to log

        Returns:
            str: Comprehensive response log string
        """
        try:
            # Attempt to parse JSON response
            try:
                response_body = json.dumps(response1.json(), indent=2)
            except (ValueError, json.JSONDecodeError):
                # Fallback to text if not JSON
                response_body = response1.text[:1000]  # Limit body size
        except Exception:
            response_body = "(Unable to decode response body)"

        response_log = f"""
    HTTPX Response Log:
    - Timestamp: {datetime.datetime.now().isoformat()}
    - Status Code: {response1.status_code}
    - URL: {response1.request.url}
    - Method: {response1.request.method}
    - Response Headers:
    {json.dumps(dict(response1.headers), indent=2)}
    - Response Body:
    {response_body}
    - Response Encoding: {response1.encoding}
    - Response Elapsed Time: {response1.elapsed}
    """.strip()

        return response_log

    # noinspection PyMethodMayBeStatic
    async def pipe(
        self,
        body: Dict[str, Any],
        __request__: Optional[Request] = None,
        __user__: Optional[Dict[str, Any]] = None,
        __event_emitter__: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        __event_call__: Optional[
            Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
        ] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Main pipe method supporting both streaming and non-streaming responses
        """
        await self.emit_status(
            __event_emitter__,
            "info",
            "Working...",
            False,
        )
        logger.debug(f"pipe:{__name__}")

        logger.debug("=== body ===")
        logger.debug(body)
        logger.debug("==== End of body ===")
        logger.debug(f"__request__: {__request__}")
        logger.debug(f"__user__: {__user__}")
        logger.debug("==== Request Url ====")
        logger.debug(__request__.url if __request__ else "No request URL provided")
        logger.debug("==== End of Request Url ====")

        assert __request__ is not None, "Request object must be provided."

        # logger.debug the Authorization header if available
        auth_header = __request__.headers.get("Authorization")
        if auth_header:
            logger.debug(f"Authorization header: {auth_header}")
        else:
            logger.debug("No Authorization header found.")

        auth_token: str | None = __request__.cookies.get("oauth_id_token")
        logger.debug(f"auth_token: {auth_token}")

        open_api_base_url: str | None = self.valves.OPENAI_API_BASE_URL
        if open_api_base_url is None:
            logger.debug(
                "LanguageModelGateway::pipe OPENAI_API_BASE_URL is not set in valves, trying environment variable."
            )
            open_api_base_url = self.read_base_url()
            logger.debug(
                f"LanguageModelGateway::pipe after trying environment variable OpenAI API_BASE_URL: {open_api_base_url}"
            )
        assert open_api_base_url is not None, (
            "LanguageModelGateway::pipe OpenAI_API_BASE_URL must be set as an environment variable."
        )
        assert open_api_base_url is not None, (
            "LanguageModelGateway::pipe OpenAI_API_BASE_URL must be set as an environment variable."
        )
        logger.debug(f"open_api_base_url: {open_api_base_url}")

        # Extract model id from the model name
        model_id = body["model"][body["model"].find(".") + 1 :]

        # Update the model id in the body
        payload = {**body, "model": model_id}

        # replace host with the OpenAI API base URL.  use proper urljoin to handle paths correctly
        # include any query parameters in the URL
        operation_path = str(__request__.url).replace(
            "https://aiden.bwell.zone/api/", ""
        )
        logger.debug(f"operation_path: {operation_path}")
        url = self.pathlib_url_join(base_url=open_api_base_url, path=operation_path)
        response_text: str = ""

        v = 11

        is_streaming: bool = body.get("stream", False)

        try:
            logger.debug(
                f"LanguageModelGateway::pipe Calling chat completion url: {url} with payload: {payload} and headers: {__request__.headers}"
            )

            # now run the __request__ with the OpenAI API
            # Headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            }
            # set User-Agent to the one from the request, if available
            if "User-Agent" in __request__.headers:
                headers["User-Agent"] = __request__.headers["User-Agent"]
            # set Referrer to the one from the request, if available
            if "Referrer" in __request__.headers:
                headers["Referrer"] = __request__.headers["Referrer"]
            # set Cookie to the one from the request, if available
            if "Cookie" in __request__.headers:
                headers["Cookie"] = __request__.headers["Cookie"]
            # set traceparent to the one from the request, if available
            if "traceparent" in __request__.headers:
                headers["traceparent"] = __request__.headers["traceparent"]
            if "origin" in __request__.headers:
                headers["Origin"] = __request__.headers["origin"]
            if "Accept-Encoding" in __request__.headers:
                headers["Accept-Encoding"] = __request__.headers["Accept-Encoding"]

            # copy any headers that start with "x-"
            for key, value in __request__.headers.items():
                if key.lower().startswith("x-"):
                    headers[key] = value

            if self.valves.debug_mode:
                yield url + "\n"
                yield f"Original Headers: {dict(__request__.headers)}" + "\n"
                yield f"New Headers: {dict(headers)}" + "\n"
                yield json.dumps(payload) + "\n"

            # Use httpx.post for a plain POST request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=url,
                    json=payload,
                    headers=headers,
                    timeout=30.0,
                    follow_redirects=True,
                )
                # Raise an exception for HTTP errors
                response.raise_for_status()

                # # Handle streaming or regular response
                content_type = response.headers.get("content-type", "")
                if content_type.startswith("text/event-stream"):
                    # Stream mode: yield lines as they arrive
                    async for line in response.aiter_lines():
                        if line:
                            yield line + "\n"
                else:
                    # Non-streaming mode: collect and return full JSON response
                    yield response.json()

            await self.emit_status(__event_emitter__, "info", "Done", True)
        except httpx.HTTPStatusError as e:
            yield (
                f"LanguageModelGateway::pipe HTTP Status Error [{v}]:"
                + f" {type(e)} {e}\n"
                + f"{self.log_httpx_request(e.request)}\n"
                + f"{self.log_response_as_string(e.response)}"
            )
        except Exception as e:
            # logger.error(f"Error in pipe: {e}")
            # logger.debug(f"Error details: {e.__traceback__}")
            httpx_version = httpx.__version__
            if is_streaming:
                error_chunk = {
                    "id": "chatcmpl-error",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "error",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": f"Error: {str(e)}"},
                            "finish_reason": "stop",
                        }
                    ],
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
            else:
                yield f"LanguageModelGateway::pipe Error [{v}]: {type(e)} {e} {httpx_version=} [{url=}] original=[{__request__.url}] {response_text=} {payload=}\n"

            await self.emit_status(__event_emitter__, "error", str(e), True)

    async def get_models(self) -> list[dict[str, str]]:
        """
        Fetches the list of available models from the OpenAI API.
        Returns:
            A list of dictionaries containing model IDs and names.

        """
        open_api_base_url: str | None = self.valves.OPENAI_API_BASE_URL
        if open_api_base_url is None:
            logger.debug(
                "LanguageModelGateway:Pipes OPENAI_API_BASE_URL is not set in valves, trying environment variable."
            )
            open_api_base_url = self.read_base_url()
            logger.debug(
                f"LanguageModelGateway:Pipes after trying environment variable OpenAI API_BASE_URL: {open_api_base_url}"
            )
        if open_api_base_url is None:
            return []
        assert open_api_base_url is not None, (
            "LanguageModelGateway:Pipes OpenAI_API_BASE_URL must be set as an environment variable."
        )
        model_url = self.pathlib_url_join(base_url=open_api_base_url, path="models")
        # call the models endpoint to get the list of available models
        logger.debug(f"Calling models endpoint: {model_url}")
        models: list[dict[str, str]] = []
        async with httpx.AsyncClient() as client:
            # Perform the GET request with a timeout
            response = await client.get(
                url=model_url,
                timeout=30.0,  # 30 seconds timeout
            )

            # Raise an exception for HTTP errors
            response.raise_for_status()

            # Parse JSON and extract 'data' key, defaulting to empty list
            models = response.json().get("data", [])
        logger.debug(f"Received models from {model_url}: {models}")
        if self.valves.restrict_to_model_ids:
            # Filter models based on the restricted model IDs
            models = [
                model
                for model in models
                if model["id"] in self.valves.restrict_to_model_ids
            ]
            logger.debug(f"Filtered models: {models}")
        return [
            {
                "id": model["id"],
                "name": model["id"],
            }
            for model in models
        ]

    async def pipes(self) -> list[dict[str, str]]:
        if self.pipelines is None:
            logger.debug("Fetching models for the first time.")
            self.pipelines = await self.get_models()
        return self.pipelines or []
