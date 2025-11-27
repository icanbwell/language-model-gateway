"""
title: LangChain Pipe Function (Streaming Version with File Support)
author: Imran Qureshi @ b.well Connected Health (mailto:imran.qureshi@bwell.com)
author_url: https://github.com/imranq2
version: 0.3.0

This module defines a Pipe class that reads the oauth_id_token from the request cookies
and uses it in Authorization header to make requests to the OpenAI API.
It supports both streaming and non-streaming responses, with file content handling.
"""

import base64
import datetime
import io
import json
import logging
import os
import time
import uuid
from pathlib import PurePosixPath
from typing import (
    AsyncGenerator,
    List,
    Optional,
    Callable,
    Awaitable,
    Any,
    Dict,
    Generator,
)
from urllib.parse import urlparse, urlunparse

import httpx
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.datastructures import Headers
from fastapi import UploadFile

# Import OpenWebUI file handling functions
try:
    from open_webui.routers.files import upload_file  # type: ignore[import-not-found]
    from open_webui.models.users import Users, UserModel # type: ignore[import-not-found]

    FILE_SUPPORT_AVAILABLE = True
except ImportError:
    FILE_SUPPORT_AVAILABLE = False
    logging.warning(
        "OpenWebUI file support not available. File handling will be disabled."
    )

logger = logging.getLogger(__name__)

# Cache TTL in seconds (60 minutes)
CACHE_TTL_SECONDS = 60 * 60
LLM_CALL_TIMEOUT = 60 * 5  # 5 minutes


class Pipe:
    """
    Pipe class for interacting with the OpenAI API using OAuth ID token from request cookies.
    Supports both streaming and non-streaming responses, with file content handling.
    """

    class Valves(BaseModel):
        emit_interval: float = Field(
            default=2.0, description="Interval in seconds between status emissions"
        )
        enable_status_indicator: bool = Field(
            default=True, description="Enable or disable status indicator emissions"
        )
        OPENAI_API_BASE_URL: Optional[str] = Field(
            default=None,
            description="Base URL for OpenAI API, e.g., https://api.openai.com/v1",
        )
        model_name_prefix: str = Field(
            default="MCP: ", description="Prefix for model names in the dropdown"
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
        enable_file_handling: bool = Field(
            default=True,
            description="Enable file handling and upload capabilities",
        )

    def __init__(self) -> None:
        self.type: str = "pipe"
        self.id: str = "language_model_gateway"
        openai_api_base_url_: Optional[str] = self.read_base_url()
        self.valves = self.Valves(OPENAI_API_BASE_URL=openai_api_base_url_)
        self.name: str = self.valves.model_name_prefix
        self.last_emit_time: float = 0
        self.pipelines: Optional[List[Dict[str, Any]]] = None
        self.pipelines_last_updated: Optional[float] = None

    @staticmethod
    def read_base_url() -> Optional[str]:
        """Reads the OpenAI API base URL from environment variables."""
        return os.getenv("LANGUAGE_MODEL_GATEWAY_API_BASE_URL") or os.getenv(
            "OPENAI_API_BASE_URL"
        )

    async def on_startup(self) -> None:
        logger.debug(f"on_startup:{__name__}")
        self.pipelines = await self.get_models()

    async def on_shutdown(self) -> None:
        logger.debug(f"on_shutdown:{__name__}")

    async def on_valves_updated(self) -> None:
        logger.debug(f"on_valves_updated:{__name__}")
        self.pipelines = await self.get_models()

    async def emit_status(
        self,
        __event_emitter__: Optional[Callable[[Dict[str, Any]], Awaitable[None]]],
        level: str,
        message: str,
        done: bool,
        message_type: str = "status",
    ) -> None:
        """Emit status updates at controlled intervals."""
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
                    "type": message_type,
                    "data": {
                        "status": "complete" if done else "in_progress",
                        "level": level,
                        "description": message,
                        "done": done,
                    },
                }
            )
            self.last_emit_time = current_time

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

    @staticmethod
    def _build_headers(
        *,
        request: Request,
        user: Optional[Dict[str, Any]],
        access_token: Optional[str],
        id_token: Optional[str],
        session_id: Optional[str],
        chat_id: Optional[str],
        message_id: Optional[str],
    ) -> Dict[str, str]:
        """
        Build headers for the OpenAI API request, including user and request context.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "X-ID-Token": id_token or "",
            "X-Session-Id": session_id or "",
            "X-Chat-Id": chat_id or "",
            "X-Message-Id": message_id or "",
        }

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

    def _yield_debug_info(
        self,
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

    @staticmethod
    def _make_error_chunk(
        *, error: Exception, is_streaming: bool
    ) -> Optional[Dict[str, Any]]:
        if is_streaming:
            return {
                "id": "chatcmpl-error",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "error",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": f"Error [{type(error).__name__}]: {error}"
                        },
                        "finish_reason": "stop",
                    }
                ],
            }
        return None

    def _upload_file_to_openwebui(
        self,
        *,
        request: Request,
        user_dict: Dict[str, Any],
        file_content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        """
        Upload file to OpenWebUI and return markdown reference.

        Args:
            request: FastAPI request object
            user_dict: User dictionary from __user__
            file_content: File content as bytes
            filename: Name for the file
            mime_type: MIME type of the file

        Returns:
            Markdown formatted string with file URL
        """
        if not FILE_SUPPORT_AVAILABLE:
            logger.warning("File support not available. Cannot upload file.")
            return f"[File: {filename}] (upload not available)"

        try:
            # Get user model from user dict
            user: UserModel = Users.get_user_by_id(user_dict["id"])

            # Create UploadFile object
            upload_file_obj = UploadFile(
                file=io.BytesIO(file_content),
                filename=filename,
                headers=Headers({"content-type": mime_type}),
            )

            # Upload to OpenWebUI
            file_item = upload_file(
                request=request,
                file=upload_file_obj,
                user=user,
                file_metadata={"mime_type": mime_type},
            )

            # Generate URL for the file
            file_url: str = request.app.url_path_for(
                "get_file_content_by_id", id=file_item.id
            )

            logger.info(f"Successfully uploaded file: {filename} (ID: {file_item.id})")

            # Return markdown formatted reference
            if mime_type.startswith("image/"):
                return f"![{filename}]({file_url})"
            else:
                return f"[{filename}]({file_url})"

        except Exception as e:
            logger.error(f"Error uploading file to OpenWebUI: {e}", exc_info=True)
            return f"[File: {filename}] (upload failed: {str(e)})"

    def _extract_file_from_response(
        self, *, response_data: Dict[str, Any]
    ) -> Optional[tuple[bytes, str, str]]:
        """
        Extract file data from API response if present.

        This method looks for the 'x_files' field in the response.
        Your external API should return files in this format:
        {
            "x_files": [
                {
                    "content": "base64_encoded_data",
                    "filename": "chart.png",
                    "mime_type": "image/png"
                }
            ]
        }

        Args:
            response_data: The JSON response from the API

        Returns:
            Tuple of (file_content, filename, mime_type) or None
        """
        # Check for custom x_files field
        if "x_files" in response_data and isinstance(response_data["x_files"], list):
            for file_info in response_data["x_files"]:
                try:
                    file_content = base64.b64decode(file_info.get("content", ""))
                    filename = file_info.get("filename", f"file-{uuid.uuid4().hex}")
                    mime_type = file_info.get("mime_type", "application/octet-stream")

                    logger.info(
                        f"Extracted file from x_files: {filename} ({mime_type}, {len(file_content)} bytes)"
                    )
                    return file_content, filename, mime_type

                except Exception as e:
                    logger.error(f"Error decoding file from x_files: {e}")
                    continue

        return None

    async def _process_streaming_response_with_files(
        self,
        *,
        response: httpx.Response,
        request: Request,
        user: Dict[str, Any],
    ) -> AsyncGenerator[str, None]:
        """
        Process streaming response and handle file data at the end of stream.

        Args:
            response: HTTPX response object
            request: FastAPI request object
            user: User dictionary

        Yields:
            Response lines in SSE format
        """
        async for line in response.aiter_lines():
            if not line:
                continue

            # Check if this is a data line with JSON
            if line.startswith("data: ") and line != "data: [DONE]":
                try:
                    json_str = line[6:]  # Remove "data: " prefix
                    chunk_data = json.loads(json_str)

                    # Check if this chunk contains file data
                    if "x_files" in chunk_data and self.valves.enable_file_handling:
                        files = chunk_data["x_files"]

                        logger.info(f"Found {len(files)} file(s) in streaming response")

                        # Process each file
                        for file_info in files:
                            try:
                                file_content = base64.b64decode(
                                    file_info.get("content", "")
                                )
                                filename = file_info.get(
                                    "filename", f"file-{uuid.uuid4().hex}"
                                )
                                mime_type = file_info.get(
                                    "mime_type", "application/octet-stream"
                                )

                                logger.debug(
                                    f"Processing file: {filename} ({mime_type}, {len(file_content)} bytes)"
                                )

                                # Upload file to OpenWebUI
                                file_markdown = self._upload_file_to_openwebui(
                                    request=request,
                                    user_dict=user,
                                    file_content=file_content,
                                    filename=filename,
                                    mime_type=mime_type,
                                )

                                # Send additional chunk with file reference
                                file_chunk = {
                                    "id": chunk_data.get(
                                        "id", f"chatcmpl-{uuid.uuid4().hex}"
                                    ),
                                    "object": "chat.completion.chunk",
                                    "created": chunk_data.get(
                                        "created", int(time.time())
                                    ),
                                    "model": chunk_data.get("model", ""),
                                    "choices": [
                                        {
                                            "index": 0,
                                            "delta": {
                                                "content": f"\n\n{file_markdown}"
                                            },
                                            "finish_reason": None,
                                        }
                                    ],
                                }
                                yield f"data: {json.dumps(file_chunk)}\n\n"

                            except Exception as e:
                                logger.error(
                                    f"Error processing file in stream: {e}",
                                    exc_info=True,
                                )
                                # Send error message as a chunk
                                error_chunk = {
                                    "id": chunk_data.get(
                                        "id", f"chatcmpl-{uuid.uuid4().hex}"
                                    ),
                                    "object": "chat.completion.chunk",
                                    "created": chunk_data.get(
                                        "created", int(time.time())
                                    ),
                                    "model": chunk_data.get("model", ""),
                                    "choices": [
                                        {
                                            "index": 0,
                                            "delta": {
                                                "content": f"\n\n*Error processing file: {str(e)}*"
                                            },
                                            "finish_reason": None,
                                        }
                                    ],
                                }
                                yield f"data: {json.dumps(error_chunk)}\n\n"

                        # Remove x_files from the chunk before passing through
                        chunk_data.pop("x_files", None)

                        # Pass through the modified chunk (if it has content)
                        if chunk_data.get("choices"):
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                        continue

                except json.JSONDecodeError:
                    pass  # Not JSON, just pass through

            # Pass through the original line
            yield line + "\n"

    async def _process_non_streaming_response_with_files(
        self,
        *,
        response_data: Dict[str, Any],
        request: Request,
        user: Dict[str, Any],
    ) -> str:
        """
        Process non-streaming response and handle any file content.

        Args:
            response_data: JSON response data
            request: FastAPI request object
            user: User dictionary

        Returns:
            Modified response JSON string
        """
        # Check if response contains file data
        file_info = self._extract_file_from_response(response_data=response_data)

        if file_info and self.valves.enable_file_handling:
            file_content, filename, mime_type = file_info

            logger.info(f"Processing file in non-streaming response: {filename}")

            # Upload file to OpenWebUI
            file_markdown = self._upload_file_to_openwebui(
                request=request,
                user_dict=user,
                file_content=file_content,
                filename=filename,
                mime_type=mime_type,
            )

            # Modify response to include file reference
            if "choices" in response_data and len(response_data["choices"]) > 0:
                choice = response_data["choices"][0]
                if "message" in choice:
                    current_content = choice["message"].get("content", "")
                    choice["message"]["content"] = (
                        f"{current_content}\n\n{file_markdown}"
                    )

            # Remove x_files from response
            response_data.pop("x_files", None)

        return json.dumps(response_data)

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
        Main pipe method supporting both streaming and non-streaming responses with file handling.
        """
        if not __oauth_token__ or "access_token" not in __oauth_token__:
            yield "Oops, looks like your Auth token has expired. Please logout and login to Aiden to get a new Auth token."
            return

        access_token: Optional[str] = __oauth_token__.get("access_token")
        id_token: Optional[str] = __oauth_token__.get("id_token")

        await self.emit_status(__event_emitter__, "info", "Working...", False)

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

        is_streaming: bool = body.get("stream", False)

        headers = self._build_headers(
            request=__request__,
            user=__user__,
            access_token=access_token,
            id_token=id_token,
            session_id=__session_id__,
            chat_id=__chat_id__,
            message_id=__message_id__,
        )

        for debug_line in self._yield_debug_info(
            user=__user__,
            request=__request__,
            url=url,
            headers=headers,
            payload=payload,
        ):
            yield debug_line

        try:
            logger.debug(
                f"Calling chat completion url: {url} with payload: {payload} and headers: {__request__.headers}"
            )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=url,
                    json=payload,
                    headers=headers,
                    timeout=LLM_CALL_TIMEOUT,
                    follow_redirects=True,
                )
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")

                if content_type.startswith("text/event-stream"):
                    # Streaming response with file handling
                    logger.debug("Processing streaming response with file handling")
                    async for line in self._process_streaming_response_with_files(
                        response=response,
                        request=__request__,
                        user=__user__,
                    ):
                        yield line
                else:
                    # Non-streaming response with file handling
                    logger.debug("Processing non-streaming response with file handling")
                    response_data = response.json()
                    modified_response = (
                        await self._process_non_streaming_response_with_files(
                            response_data=response_data,
                            request=__request__,
                            user=__user__,
                        )
                    )
                    yield modified_response

            await self.emit_status(__event_emitter__, "info", "Done", True)

        except httpx.HTTPStatusError as e:
            await self.emit_status(__event_emitter__, "HttpError", f"{e}", True)
            yield (
                f"LanguageModelGateway::pipe HTTP Status Error: {type(e)} {e}\n"
                + f"{self.log_httpx_request(e.request)}\n"
                + f"{self.log_response_as_string(e.response)}"
            )
        except Exception as e:
            await self.emit_status(__event_emitter__, "error", f"{e}", True)
            httpx_version = getattr(httpx, "__version__", "unknown")
            error_chunk = self._make_error_chunk(error=e, is_streaming=is_streaming)
            if error_chunk:
                yield f"data: {json.dumps(error_chunk)}\n\n"
            else:
                yield (
                    f"LanguageModelGateway::pipe Error:"
                    f" {type(e)} {e} httpx_version={httpx_version} url={url}"
                    f" original_url={getattr(__request__, 'url', None)}"
                    f" payload={payload}\n"
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

        async with httpx.AsyncClient() as client:
            response = await client.get(url=model_url, timeout=30.0)
            response.raise_for_status()
            models = response.json().get("data", [])

        logger.debug(f"Received models from {model_url}: {models}")

        # Update cache timestamp
        self.pipelines_last_updated = time.time()

        return [{"id": model["id"], "name": model["id"]} for model in models]

    async def pipes(self) -> List[Dict[str, str]]:
        now = time.time()
        cache_expired = (
            self.pipelines is None
            or self.pipelines_last_updated is None
            or (now - self.pipelines_last_updated) > CACHE_TTL_SECONDS
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

        return models
