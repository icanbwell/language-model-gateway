"""
title: LangChain Pipe Function (Streaming Version - FIXED)
author: Imran Qureshi @ b.well Connected Health (mailto:imran.qureshi@bwell.com)
author_url: https://github.com/imranq2
version: 0.2.1

This module defines a Pipe class that reads the oauth_id_token from the request cookies
and uses it in Authorization header to make requests to the OpenAI API.
It supports both streaming and non-streaming responses.

KEY FIX: Instead of yielding raw SSE lines, we now parse the OpenAI streaming response
and yield individual text chunks that OpenWebUI will format properly.
"""

import asyncio
import datetime
import json
import logging
import os
import random
import time
from pathlib import PurePosixPath
from time import perf_counter
from typing import (
    AsyncGenerator,
    List,
    Optional,
    Callable,
    Awaitable,
    Any,
    Dict,
    Generator,
    cast,
)
from urllib.parse import urlparse, urlunparse

import httpx
from pydantic import BaseModel, Field
from starlette.requests import Request

logger = logging.getLogger(__name__)

# Cache TTL in seconds (60 minutes)
CACHE_TTL_SECONDS = 60 * 60

LLM_CALL_TIMEOUT = 60 * 5  # 5 minutes


class Pipe:
    """
    Pipe class for interacting with the OpenAI API using OAuth ID token from request cookies.
    Supports both streaming and non-streaming responses.
    """

    class Valves(BaseModel):
        enable_status_indicator: bool = Field(
            default=True, description="Enable or disable status indicator emissions"
        )
        OPENAI_API_BASE_URL: Optional[str] = Field(
            default=None,
            description="Base URL for OpenAI API, e.g., https://api.openai.com/v1",
        )
        model_name_prefix: Optional[str] = Field(
            default=None, description="Prefix for model names in the dropdown"
        )
        restrict_to_admins: bool = Field(
            default=False,
            description="Restrict access to this pipe to admin users only",
        )
        restrict_to_model_ids: List[str] = Field(
            default_factory=list,
            description="List of model IDs to restrict access to. If empty, no restriction is applied.",
        )
        debug_mode: bool = Field(
            default=False,
            description="Enable debug mode for additional logging and debugging information",
        )
        default_model: Optional[str] = Field(
            default="General Purpose", description="Default model to use"
        )
        # New valves for previously hardcoded constants
        model_cache_ttl_seconds: int = Field(
            default=CACHE_TTL_SECONDS,
            description="Cache TTL in seconds for the models list",
        )
        llm_call_timeout_seconds: float = Field(
            default=LLM_CALL_TIMEOUT,
            description="Timeout in seconds for LLM chat/completions API calls",
        )
        models_list_timeout_seconds: float = Field(
            default=30.0,
            description="Timeout in seconds for fetching the models list",
        )
        stream: Optional[bool] = Field(
            default=True,
            description="Whether to use streaming responses for the chat/completions endpoint",
        )
        client_id_header_value: Optional[str] = Field(
            default="Aiden",
            description="Header name to pass client ID for debugging purposes",
        )

    def __init__(self) -> None:
        self.type: str = "pipe"
        self.id: str = "language_model_gateway"
        openai_api_base_url_ = self.read_base_url()
        self.valves = self.Valves(OPENAI_API_BASE_URL=openai_api_base_url_)
        self.name: str = (
            self.valves.model_name_prefix.strip()
            if self.valves.model_name_prefix
            else ""
        )
        self.pipelines: Optional[List[Dict[str, Any]]] = None
        self.pipelines_last_updated: Optional[float] = (
            None  # Track last cache update time
        )

    @staticmethod
    def read_base_url() -> Optional[str]:
        """Reads the OpenAI API base URL from environment variables."""
        return os.getenv("LANGUAGE_MODEL_GATEWAY_API_BASE_URL") or os.getenv(
            "OPENAI_API_BASE_URL"
        )

    async def on_startup(self) -> None:
        logger.debug(f"on_startup:{__name__}")
        self.pipelines = await self.get_models()

    # noinspection PyMethodMayBeStatic
    async def on_shutdown(self) -> None:
        logger.debug(f"on_shutdown:{__name__}")

    async def on_valves_updated(self) -> None:
        logger.debug(f"on_valves_updated:{__name__}")
        self.pipelines = await self.get_models()

    @staticmethod
    async def _emit_status(
        event_emitter: Optional[Callable[[Dict[str, Any]], Awaitable[None]]],
        description: str,
        done: bool = False,
    ) -> None:
        """Emit a native OpenWebUI status bar update."""
        if event_emitter:
            await event_emitter(
                {
                    "type": "status",
                    "data": {"description": description, "done": done},
                }
            )

    @staticmethod
    async def _emit_completion(
        event_emitter: Optional[Callable[[Dict[str, Any]], Awaitable[None]]],
        *,
        content: str = "",
        usage: Optional[Dict[str, Any]] = None,
        done: bool = True,
    ) -> None:
        """Emit a chat:completion event with optional usage statistics."""
        if event_emitter:
            data: Dict[str, Any] = {"done": done, "content": content}
            if usage is not None:
                data["usage"] = usage
            await event_emitter({"type": "chat:completion", "data": data})

    @staticmethod
    async def _emit_error(
        event_emitter: Optional[Callable[[Dict[str, Any]], Awaitable[None]]],
        message: str,
        done: bool = True,
    ) -> None:
        """Emit a native OpenWebUI error via the chat:completion event."""
        if event_emitter:
            await event_emitter(
                {
                    "type": "chat:completion",
                    "data": {"error": {"message": message}, "done": done},
                }
            )

    @staticmethod
    def _create_thinking_tasks(
        event_emitter: Optional[Callable[[Dict[str, Any]], Awaitable[None]]],
    ) -> List[asyncio.Task[None]]:
        """Schedule progressive thinking status messages.

        Returns a list of asyncio tasks that emit status updates at
        staggered intervals, giving the user visual feedback while
        waiting for the first response token.
        """
        if not event_emitter:
            return []

        async def _later(delay: float, msg: str) -> None:
            await asyncio.sleep(delay)
            await event_emitter({"type": "status", "data": {"description": msg}})

        tasks: List[asyncio.Task[None]] = []
        for delay, msg in [
            (0, "Thinking\u2026"),
            (1.5, "Reading the question\u2026"),
            (4.0, "Gathering thoughts\u2026"),
            (6.0, "Exploring possible responses\u2026"),
            (8.0, "Building a response\u2026"),
        ]:
            tasks.append(
                asyncio.create_task(
                    _later(delay + random.uniform(0, 0.5), msg)
                )
            )
        return tasks

    @staticmethod
    def _cancel_thinking(tasks: List[asyncio.Task[None]]) -> None:
        """Cancel all pending thinking status tasks."""
        for t in tasks:
            t.cancel()
        tasks.clear()

    @classmethod
    def pathlib_url_join(cls, base_url: str, path: str) -> str:
        """Join URLs using pathlib for path manipulation."""
        parsed_base = urlparse(base_url)
        full_path = str(PurePosixPath(parsed_base.path) / path.lstrip("/"))
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
        """Convert an HTTPX request to a detailed string representation."""
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
        """Convert an HTTPX response to a detailed, formatted string."""
        try:
            try:
                response_body = json.dumps(response1.json(), indent=2)
            except (ValueError, json.JSONDecodeError):
                response_body = response1.text[:1000]
        except Exception:
            response_body = "(Unable to decode response body)"
        response_log = f"""
HTTPX Response Log:
- Timestamp: {datetime.datetime.now().isoformat()}
- Status Code: {response1.status_code}
- URL: {response1.request.url}
- Method: {response1.request.method}
- Response Headers: {json.dumps(dict(response1.headers), indent=2)}
- Response Body: {response_body}
- Response Encoding: {response1.encoding}
- Response Elapsed Time: {response1.elapsed}
""".strip()
        return response_log

    def _build_headers(
        self,
        *,
        request: Request,
        user: Optional[Dict[str, Any]],
        access_token: Optional[str],
        id_token: Optional[str],
        session_id: Optional[str],
        chat_id: Optional[str],
        message_id: Optional[str],
        debug_mode: bool,
    ) -> Dict[str, str]:
        """
        Build headers for the OpenAI API request, including user and request context.

        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {access_token}",
            "X-ID-Token": id_token or "",
            "X-Session-Id": session_id or "",
            "X-Chat-Id": chat_id or "",
            "X-Message-Id": message_id or "",
        }
        if debug_mode:
            headers["Debug-Mode"] = "true"
        if self.valves.client_id_header_value:
            headers["X-Client-Id"] = self.valves.client_id_header_value

        # pass through some headers from OpenWebUI request to OpenAI API for better context and debugging
        for key in [
            "User-Agent",
            "Referrer",
            "Cookie",
            "traceparent",
            "origin",
            "Accept-Encoding",
        ]:
            if key in request.headers:
                headers[key] = request.headers[key]
        if user:
            for user_key, header_key in [
                ("name", "X-OpenWebUI-User-Name"),
                ("id", "X-OpenWebUI-User-Id"),
                ("email", "X-OpenWebUI-User-Email"),
                ("role", "X-OpenWebUI-User-Role"),
            ]:
                if user.get(user_key):
                    headers[header_key] = user[user_key]
            info = user.get("info")
            if info and isinstance(info, dict) and info.get("location"):
                headers["X-OpenWebUI-User-Location"] = info["location"]
        for key, value in request.headers.items():
            if key.lower().startswith("x-"):
                headers[key] = value
        return headers

    @staticmethod
    def _extract_user_prompt(body: Dict[str, Any]) -> Optional[str]:
        messages = body.get("messages")
        if not isinstance(messages, list):
            return None
        for message in reversed(messages):
            if not isinstance(message, dict):
                continue
            if message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") == "text" and isinstance(item.get("text"), str):
                        return cast(str, item["text"])
            if isinstance(content, dict):
                text = content.get("text")
                if isinstance(text, str):
                    return text
        return None

    @classmethod
    def _is_debug_request(cls, body: Dict[str, Any]) -> bool:
        prompt = cls._extract_user_prompt(body)
        if not prompt:
            return False
        return prompt.lstrip().startswith("DEBUG:")

    def _yield_debug_info(
        self,
        *,
        user: Optional[Dict[str, Any]],
        request: Request,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
    ) -> Generator[str, None, None]:
        if self.valves.debug_mode:
            yield f"User:\n{json.dumps(user, indent=2) if user else None}\n"
            yield f"Original Headers:\n{dict(request.headers)}\n"
            yield url + "\n"
            yield f"New Headers: {dict(headers)}\n"
            yield json.dumps(payload) + "\n"
            info = user.get("info") if user else None
            if info and isinstance(info, dict) and info.get("location"):
                yield f"Location: {type(info['location']).__name__} {info['location']}\n"

    async def _stream_openai_response(
        self,
        response: httpx.Response,
        event_emitter: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        thinking_tasks: Optional[List[asyncio.Task[None]]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Parse OpenAI Chat Completions streaming response and yield text chunks.

        Uses a byte-buffer approach for robust SSE parsing: reads raw chunks
        and manually splits on newlines. This correctly handles partial frames
        that may be split across network chunks, unlike aiter_lines() which
        can mishandle SSE's double-newline delimiters.

        Emits native status updates:
        - Cancels thinking tasks and emits "Responding…" on first content token
        - Forwards usage statistics from the final chunk via chat:completion

        Yields plain text content only — OpenWebUI handles SSE wrapping.
        """
        first_token_received = False
        usage: Optional[Dict[str, Any]] = None

        buf = bytearray()
        async for chunk in response.aiter_bytes():
            buf.extend(chunk)
            start_idx = 0
            # Process all complete lines in the buffer
            while True:
                newline_idx = buf.find(b"\n", start_idx)
                if newline_idx == -1:
                    break

                line = buf[start_idx:newline_idx].strip()
                start_idx = newline_idx + 1

                # Skip empty lines and SSE comments (lines starting with ':')
                if not line or line.startswith(b":"):
                    continue

                # Only process lines with the "data:" prefix
                if not line.startswith(b"data:"):
                    continue

                data_part = line[5:].strip()

                # End of SSE stream
                if data_part == b"[DONE]":
                    # Forward usage stats to OpenWebUI
                    if usage:
                        await self._emit_completion(
                            event_emitter, usage=usage, done=False
                        )
                    return

                try:
                    chunk_json = json.loads(data_part.decode("utf-8"))
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Failed to parse SSE data: {data_part!r}, error: {e}"
                    )
                    continue

                # Capture usage from the final chunk (OpenAI includes it
                # in the last chunk before [DONE] when stream_options.include_usage is set)
                if "usage" in chunk_json and chunk_json["usage"]:
                    usage = chunk_json["usage"]

                # Extract text content from Chat Completions chunk format
                choices = chunk_json.get("choices")
                if not choices:
                    continue

                delta = choices[0].get("delta", {})
                content = delta.get("content")
                if content:
                    # On first content token, cancel thinking and show "Responding"
                    if not first_token_received:
                        first_token_received = True
                        if thinking_tasks:
                            self._cancel_thinking(thinking_tasks)
                        await self._emit_status(
                            event_emitter, "Responding\u2026"
                        )
                    yield content

            # Remove processed bytes from buffer
            if start_idx > 0:
                del buf[:start_idx]

    async def pipe(
        self,
        body: Dict[str, Any],
        __request__: Optional[Request] = None,
        __user__: Optional[Dict[str, Any]] = None,
        __event_emitter__: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        __event_call__: Optional[
            Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
        ] = None,
        __oauth_token__: Optional[Dict[str, Any]] = None,
        __chat_id__: Optional[str] = None,
        __session_id__: Optional[str] = None,
        __message_id__: Optional[str] = None,
        __metadata__: Optional[Dict[str, Any]] = None,
        __files__: Optional[List[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Main pipe method supporting both streaming and non-streaming responses.

        IMPORTANT: For streaming, yield plain text chunks or structured data.
        The OpenWebUI framework handles wrapping in proper SSE format.
        """
        if not __oauth_token__ or "access_token" not in __oauth_token__:
            await self._emit_error(
                __event_emitter__,
                "Your Auth token has expired. Please logout and login to Aiden to get a new Auth token.",
            )
            return

        access_token: Optional[str] = __oauth_token__.get("access_token")
        id_token: Optional[str] = __oauth_token__.get("id_token")

        logger.debug(f"pipe:{__name__}")
        logger.debug(f"body: {body}")
        logger.debug(f"__request__: {__request__}")
        logger.debug(f"__user__: {__user__}")
        logger.debug(f"Request URL: {getattr(__request__, 'url', None)}")

        if __request__ is None:
            raise ValueError("Request object must be provided.")

        auth_header = __request__.headers.get("Authorization")
        logger.debug(f"Authorization header: {auth_header if auth_header else 'None'}")

        open_api_base_url: Optional[str] = (
            self.valves.OPENAI_API_BASE_URL or self.read_base_url()
        )
        if not open_api_base_url:
            raise RuntimeError(
                "OpenAI API base URL must be set as an environment variable."
            )
        logger.debug(f"open_api_base_url: {open_api_base_url}")

        model_id = body.get("model", "")
        if "." in model_id:
            model_id = model_id.split(".", 1)[1]

        payload = {**body, "model": model_id}
        url = self.pathlib_url_join(base_url=open_api_base_url, path="chat/completions")

        stream: Optional[bool] = self.valves.stream
        if stream is not None:
            payload["stream"] = stream

        response_text: str = ""
        is_streaming: bool = bool(payload.get("stream", False))

        debug_request = self._is_debug_request(body)
        headers = self._build_headers(
            request=__request__,
            user=__user__,
            access_token=access_token,
            id_token=id_token,
            session_id=__session_id__,
            chat_id=__chat_id__,
            message_id=__message_id__,
            debug_mode=debug_request,
        )

        for debug_line in self._yield_debug_info(
            user=__user__,
            request=__request__,
            url=url,
            headers=headers,
            payload=payload,
        ):
            yield debug_line

        # Schedule progressive thinking status indicators while waiting
        # for the first response token (streaming only)
        thinking_tasks: List[asyncio.Task[None]] = []
        if self.valves.enable_status_indicator and is_streaming:
            thinking_tasks = self._create_thinking_tasks(__event_emitter__)

        start_time = perf_counter()
        error_occurred = False

        try:
            logger.debug(
                f"Calling chat completion url: {url} with payload: {payload}"
                f" and headers: {__request__.headers}"
            )
            async with httpx.AsyncClient() as client:
                if is_streaming:
                    async with client.stream(
                        "POST",
                        url,
                        json=payload,
                        headers=headers,
                        timeout=self.valves.llm_call_timeout_seconds,
                        follow_redirects=True,
                    ) as response:
                        # Read the error body before raise_for_status() so
                        # the error message includes the server's response
                        if response.status_code >= 400:
                            error_body = await response.aread()
                            response_text = error_body.decode(
                                "utf-8", errors="replace"
                            )
                            response.raise_for_status()

                        content_type = response.headers.get("content-type", "")
                        if "text/event-stream" in content_type:
                            async for text_chunk in self._stream_openai_response(
                                response,
                                event_emitter=__event_emitter__,
                                thinking_tasks=thinking_tasks,
                            ):
                                yield text_chunk
                        else:
                            # Non-SSE response — cancel thinking immediately
                            self._cancel_thinking(thinking_tasks)
                            await self._emit_status(
                                __event_emitter__, "Responding\u2026"
                            )
                            raw_body = await response.aread()
                            response_text = raw_body.decode(
                                "utf-8", errors="replace"
                            )
                            try:
                                data = json.loads(response_text)
                                choices = data.get("choices", [])
                                if choices:
                                    message = choices[0].get("message", {})
                                    content = message.get("content", "")
                                    if content:
                                        yield content
                                    else:
                                        yield json.dumps(data)
                                else:
                                    yield json.dumps(data)
                            except json.JSONDecodeError:
                                yield response_text
                else:
                    # Non-streaming response
                    response = await client.post(
                        url=url,
                        json=payload,
                        headers=headers,
                        timeout=self.valves.llm_call_timeout_seconds,
                        follow_redirects=True,
                    )
                    response.raise_for_status()
                    yield json.dumps(response.json())

        except httpx.HTTPStatusError as e:
            error_occurred = True
            error_detail = (
                f"HTTP {e.response.status_code}: {e}\n"
                f"{self.log_httpx_request(e.request)}\n"
                f"{self.log_response_as_string(e.response)}"
            )
            logger.error(f"LanguageModelGateway::pipe {error_detail}")
            await self._emit_error(__event_emitter__, error_detail)
        except Exception as e:
            error_occurred = True
            httpx_version = getattr(httpx, "__version__", "unknown")
            error_detail = (
                f"{type(e).__name__}: {e}"
                f" | httpx={httpx_version} url={url}"
                f" original_url={getattr(__request__, 'url', None)}"
            )
            logger.error(f"LanguageModelGateway::pipe Error: {error_detail}")
            await self._emit_error(__event_emitter__, error_detail)
        finally:
            self._cancel_thinking(thinking_tasks)
            elapsed = perf_counter() - start_time
            if not error_occurred:
                await self._emit_status(
                    __event_emitter__,
                    f"Completed in {elapsed:.1f}s",
                    done=True,
                )
            else:
                await self._emit_status(
                    __event_emitter__,
                    f"Failed after {elapsed:.1f}s",
                    done=True,
                )

    async def get_models(self) -> List[Dict[str, str]]:
        """Fetches the list of available models from the OpenAI API."""
        open_api_base_url: Optional[str] = (
            self.valves.OPENAI_API_BASE_URL or self.read_base_url()
        )
        if not open_api_base_url:
            logger.debug("OpenAI API base URL is not set.")
            return []

        model_url = self.pathlib_url_join(base_url=open_api_base_url, path="models")
        logger.debug(f"Calling models endpoint: {model_url}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url=model_url, timeout=self.valves.models_list_timeout_seconds
                )
                response.raise_for_status()
                models = response.json().get("data", [])

            logger.debug(f"Received models from {model_url}: {models}")
            # Update cache timestamp
            self.pipelines_last_updated = time.time()
            return [{"id": model["id"], "name": model["id"]} for model in models]
        except httpx.TimeoutException as e:
            logger.exception(f"Timeout fetching models from {model_url}: {e}")
            return []
        except httpx.HTTPStatusError as e:
            logger.exception(
                f"HTTP error fetching models from {model_url}: {e.response.status_code}"
            )
            return []
        except Exception as e:
            logger.exception(f"Unexpected error fetching models from {model_url}: {e}")
            return []

    async def pipes(self) -> List[Dict[str, str]]:
        now = time.time()
        cache_expired = (
            self.pipelines is None
            or self.pipelines_last_updated is None
            or (now - self.pipelines_last_updated) > self.valves.model_cache_ttl_seconds
        )
        if cache_expired:
            logger.debug("Model cache expired or not set. Fetching models.")
            self.pipelines = await self.get_models()

        models = self.pipelines or []
        if self.valves.restrict_to_model_ids:
            models = [
                model
                for model in models
                if model["id"] in self.valves.restrict_to_model_ids
            ]

        # Always put default_model at the top
        default_model_id = self.valves.default_model
        if default_model_id:
            # Only insert default_model if it exists in the models list
            if any(m["id"] == default_model_id for m in self.pipelines or []):
                # Remove any existing entry for default_model
                models = [m for m in models if m["id"] != default_model_id]
                # Insert default_model at the top
                models.insert(0, {"id": default_model_id, "name": default_model_id})

        return models
