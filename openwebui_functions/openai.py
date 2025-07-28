"""title: LangChain Pipe Function (Streaming Version)
author: Imran Qureshi @ b.well Connected Health (mailto:imran.qureshi@bwell.com)
author_url: https://github.com/imranq2
version: 0.2.0
This module defines a Pipe class that reads the oauth_id_token from the request cookies and uses it in Authorization header
to make requests to the OpenAI API. It supports both streaming and non-streaming responses.
"""

import asyncio
import json
import os
import time
from pathlib import PurePosixPath
from typing import AsyncGenerator
from typing import Optional, Callable, Awaitable, Any, Dict
from typing import Union, Generator, Iterator

import requests
from pydantic import BaseModel
from pydantic import Field
from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from urllib.parse import urlparse, urlunparse


class Pipe:
    class Valves(BaseModel):
        emit_interval: float = Field(
            default=2.0, description="Interval in seconds between status emissions"
        )
        enable_status_indicator: bool = Field(
            default=True, description="Enable or disable status indicator emissions"
        )

    def __init__(self) -> None:
        self.type: str = "pipe"
        self.id: str = "language_model_gateway"
        self.valves = self.Valves()
        self.last_emit_time: float = 0

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
    ) -> Union[str, Generator[Any, None, None] | Iterator[Any]]:
        """
        Main pipe method supporting both streaming and non-streaming responses
        """
        # This is where you can add your custom pipelines like RAG.
        print(f"pipe:{__name__}")

        print("=== body ===")
        print(body)
        print("==== End of body ===")
        print(f"__request__: {__request__}")
        print(f"__user__: {__user__}")
        print("==== Request Url ====")
        print(__request__.url if __request__ else "No request URL provided")
        print("==== End of Request Url ====")

        assert __request__ is not None, "Request object must be provided."

        # print the Authorization header if available
        auth_header = __request__.headers.get("Authorization")
        if auth_header:
            print(f"Authorization header: {auth_header}")
        else:
            print("No Authorization header found.")

        auth_token: str | None = __request__.cookies.get("oauth_id_token")
        print(f"auth_token: {auth_token}")

        open_api_base_url: str | None = os.getenv("OPENAI_API_BASE_URL")
        assert open_api_base_url is not None, (
            "OpenAI_API_BASE_URL must be set as an environment variable."
        )
        print(f"open_api_base_url: {open_api_base_url}")

        headers: MutableHeaders = __request__.headers.mutablecopy()

        # if auth token is available in the cookies, add it to the Authorization header
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        # Extract model id from the model name
        model_id = body["model"][body["model"].find(".") + 1 :]

        # Update the model id in the body
        payload = {**body, "model": model_id}

        try:
            # replace host with the OpenAI API base URL.  use proper urljoin to handle paths correctly
            # include any query parameters in the URL
            operation_path = str(__request__.url).replace(
                "https://open-webui.localhost/api/", ""
            )
            print(f"operation_path: {operation_path}")
            url = self.pathlib_url_join(base_url=open_api_base_url, path=operation_path)

            print(f"url: {url}")

            # now run the __request__ with the OpenAI API
            response = requests.post(
                url=url,
                json=payload,
                headers=headers,
                stream=body.get("stream", False),
                timeout=30,  # Set a timeout for the request
            )

            response.raise_for_status()

            if body["stream"]:
                return response.iter_lines()
            else:
                return response.json()  # type: ignore[no-any-return]
        except Exception as e:
            return f"Error: {e}"

    # noinspection PyMethodMayBeStatic
    def pipes(self) -> list[dict[str, str]]:
        open_api_base_url: str | None = os.getenv("OPENAI_API_BASE_URL")
        assert open_api_base_url is not None, (
            "OpenAI_API_BASE_URL must be set as an environment variable."
        )
        model_url = self.pathlib_url_join(base_url=open_api_base_url, path="models")
        # call the models endpoint to get the list of available models
        response = requests.get(model_url, timeout=30)  # Set a timeout for the request
        response.raise_for_status()
        models = response.json().get("data", [])
        print(f"models: {models}")
        return [
            {
                "id": model["id"],
                "name": model["id"],
            }
            for model in models
        ]
