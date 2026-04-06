"""
title: LangChain Pipe Function (Streaming Version)
author: Imran Qureshi @ b.well Connected Health (mailto:imran.qureshi@bwell.com)
author_url: https://github.com/imranq2
version: 0.3.0

This module defines a Pipe class that reads the oauth_id_token from the request cookies
and uses it in Authorization header to make requests to the OpenAI API.
It supports both streaming and non-streaming responses.

Supports three API modes via the ``api_mode`` valve:
- ``chat_completions``: Standard OpenAI Chat Completions API (``/chat/completions``)
- ``responses_stateless``: OpenAI Responses API without server-side state (``/responses``)
- ``responses_stateful``: OpenAI Responses API with server-side state; uses
  ``previous_response_id`` to chain conversation turns so only the latest user
  message is sent each turn (``/responses`` with ``store: true``)
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
    Literal,
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

CACHE_TTL_SECONDS = 60 * 60
LLM_CALL_TIMEOUT = 60 * 5


class Pipe:
    """
    Pipe class for interacting with the OpenAI API using OAuth ID token from request cookies.
    Supports Chat Completions API and Responses API (stateless and stateful).
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
        model_cache_ttl_seconds: int = Field(
            default=CACHE_TTL_SECONDS,
            description="Cache TTL in seconds for the models list",
        )
        llm_call_timeout_seconds: float = Field(
            default=LLM_CALL_TIMEOUT,
            description="Timeout in seconds for LLM API calls",
        )
        models_list_timeout_seconds: float = Field(
            default=30.0,
            description="Timeout in seconds for fetching the models list",
        )
        stream: Optional[bool] = Field(
            default=True,
            description="Whether to use streaming responses",
        )
        client_id_header_value: Optional[str] = Field(
            default="Aiden",
            description="Header name to pass client ID for debugging purposes",
        )
        api_mode: Literal[
            "chat_completions", "responses_stateless", "responses_stateful"
        ] = Field(
            default="chat_completions",
            description=(
                "API mode: 'chat_completions' uses /chat/completions, "
                "'responses_stateless' uses /responses without server-side state, "
                "'responses_stateful' uses /responses with store=true and "
                "previous_response_id to chain conversation turns."
            ),
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
        self.pipelines_last_updated: Optional[float] = None
        self._response_id_by_chat: Dict[str, str] = {}

    @staticmethod
    def read_base_url() -> Optional[str]:
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

    # ── Event emitters ───────────────────────────────────────────────────

    @staticmethod
    async def _emit_status(
        emitter: Optional[Callable[[Dict[str, Any]], Awaitable[None]]],
        description: str,
        done: bool = False,
    ) -> None:
        if emitter:
            await emitter(
                {"type": "status", "data": {"description": description, "done": done}}
            )

    @staticmethod
    async def _emit_completion(
        emitter: Optional[Callable[[Dict[str, Any]], Awaitable[None]]],
        *,
        content: str = "",
        usage: Optional[Dict[str, Any]] = None,
        done: bool = True,
    ) -> None:
        if emitter:
            data: Dict[str, Any] = {"done": done, "content": content}
            if usage is not None:
                data["usage"] = usage
            await emitter({"type": "chat:completion", "data": data})

    @staticmethod
    async def _emit_error(
        emitter: Optional[Callable[[Dict[str, Any]], Awaitable[None]]],
        message: str,
    ) -> None:
        if emitter:
            await emitter(
                {
                    "type": "chat:completion",
                    "data": {"error": {"message": message}, "done": True},
                }
            )

    # ── Loading indicator ────────────────────────────────────────────────

    _LOADING_PHRASES: List[str] = [
        "\u2705 Accomplishing",
        "\u26a1 Actioning",
        "\u2728 Actualizing",
        "\U0001f3d7\ufe0f Architecting",
        "\U0001f35e Baking",
        "\U0001f526 Beaming",
        "\U0001f3b6 Beboppin'",
        "\U0001f616 Befuddling",
        "\U0001f32c\ufe0f Billowing",
        "\U0001f373 Blanching",
        "\U0001f4e2 Bloviating",
        "\U0001f57a Boogieing",
        "\U0001f939 Boondoggling",
        "\U0001f47e Booping",
        "\U0001f97e Bootstrapping",
        "\u2615 Brewing",
        "\U0001f95f Bunning",
        "\U0001f407 Burrowing",
        "\U0001f9ee Calculating",
        "\U0001f498 Canoodling",
        "\U0001f36e Caramelizing",
        "\U0001f4a7 Cascading",
        "\U0001f680 Catapulting",
        "\U0001f9e0 Cerebrating",
        "\U0001f4e1 Channeling",
        "\U0001f4e1 Channelling",
        "\U0001f483 Choreographing",
        "\U0001f300 Churning",
        "\U0001f916 Clauding",
        "\U0001f54a\ufe0f Coalescing",
        "\U0001f914 Cogitating",
        "\U0001f527 Combobulating",
        "\U0001f3b5 Composing",
        "\U0001f4bb Computing",
        "\U0001f9ea Concocting",
        "\U0001f4ad Considering",
        "\U0001f4ad Contemplating",
        "\U0001f373 Cooking",
        "\U0001f3a8 Crafting",
        "\u2728 Creating",
        "\U0001f4aa Crunching",
        "\U0001f48e Crystallizing",
        "\U0001f331 Cultivating",
        "\U0001f50d Deciphering",
        "\u2696\ufe0f Deliberating",
        "\U0001f3af Determining",
        "\u23f3 Dilly-dallying",
        "\U0001f635 Discombobulating",
        "\U0001f4aa Doing",
        "\u270f\ufe0f Doodling",
        "\U0001f327\ufe0f Drizzling",
        "\U0001f30a Ebbing",
        "\u2705 Effecting",
        "\U0001f4a1 Elucidating",
        "\U0001f380 Embellishing",
        "\U0001fa84 Enchanting",
        "\U0001f52e Envisioning",
        "\U0001f32b\ufe0f Evaporating",
        "\U0001f37a Fermenting",
        "\U0001f3bb Fiddle-faddling",
        "\U0001f9d0 Finagling",
        "\U0001f525 Flambing",
        "\U0001f47b Flibbertigibbeting",
        "\U0001f30a Flowing",
        "\U0001f633 Flummoxing",
        "\U0001f98b Fluttering",
        "\U0001f525 Forging",
        "\U0001f9f1 Forming",
        "\U0001f938 Frolicking",
        "\U0001f9c1 Frosting",
        "\U0001f6b6 Gallivanting",
        "\U0001f40e Galloping",
        "\U0001f33f Garnishing",
        "\u2699\ufe0f Generating",
        "\U0001f44b Gesticulating",
        "\U0001f33e Germinating",
        "\U0001f4be Gitifying",
        "\U0001f3b6 Grooving",
        "\U0001f4a8 Gusting",
        "\U0001f3b6 Harmonizing",
        "#\ufe0f\u20e3 Hashing",
        "\U0001f423 Hatching",
        "\U0001f42e Herding",
        "\U0001f4ef Honking",
        "\U0001f389 Hullaballooing",
        "\U0001f680 Hyperspacing",
        "\U0001f4a1 Ideating",
        "\U0001f4ad Imagining",
        "\U0001f3b7 Improvising",
        "\U0001f95a Incubating",
        "\U0001f9e0 Inferring",
        "\U0001f375 Infusing",
        "\u26a1 Ionizing",
        "\U0001f57a Jitterbugging",
        "\U0001f52a Julienning",
        "\U0001f35e Kneading",
        "\U0001f35e Leavening",
        "\U0001fa84 Levitating",
        "\U0001f634 Lollygagging",
        "\u2728 Manifesting",
        "\U0001f356 Marinating",
        "\U0001f6b6 Meandering",
        "\U0001f98b Metamorphosing",
        "\U0001f32b\ufe0f Misting",
        "\U0001f576\ufe0f Moonwalking",
        "\U0001f6b6 Moseying",
        "\U0001f914 Mulling",
        "\U0001f4aa Mustering",
        "\U0001f3b6 Musing",
        "\U0001f32b\ufe0f Nebulizing",
        "\U0001f426 Nesting",
        "\U0001f4f0 Newspapering",
        "\U0001f35c Noodling",
        "\u269b\ufe0f Nucleating",
        "\U0001f6f0\ufe0f Orbiting",
        "\U0001f3bc Orchestrating",
        "\U0001f4a7 Osmosing",
        "\U0001f6b6 Perambulating",
        "\u2615 Percolating",
        "\U0001f4d6 Perusing",
        "\U0001f914 Philosophising",
        "\U0001f33b Photosynthesizing",
        "\U0001f41d Pollinating",
        "\U0001f914 Pondering",
        "\U0001f9d0 Pontificating",
        "\U0001f43e Pouncing",
        "\U0001f327\ufe0f Precipitating",
        "\U0001f3a9 Prestidigitating",
        "\u2699\ufe0f Processing",
        "\U0001f4cb Proofing",
        "\U0001f331 Propagating",
        "\U0001f527 Puttering",
        "\U0001f9e9 Puzzling",
        "\u269b\ufe0f Quantumizing",
        "\u2728 Razzle-dazzling",
        "\U0001f3b7 Razzmatazzing",
        "\U0001f527 Recombobulating",
        "\U0001f578\ufe0f Reticulating",
        "\U0001f413 Roosting",
        "\U0001f404 Ruminating",
        "\U0001f373 Sauting",
        "\U0001f401 Scampering",
        "\U0001f6b6 Schlepping",
        "\U0001f401 Scurrying",
        "\U0001f9c2 Seasoning",
        "\U0001f608 Shenaniganing",
        "\U0001f483 Shimmying",
        "\U0001f372 Simmering",
        "\U0001f3c3 Skedaddling",
        "\u270f\ufe0f Sketching",
        "\U0001f40d Slithering",
        "\U0001f917 Smooshing",
        "\U0001f9e6 Sock-hopping",
        "\u26f0\ufe0f Spelunking",
        "\U0001f300 Spinning",
        "\U0001f33f Sprouting",
        "\U0001f372 Stewing",
        "\U0001f4a8 Sublimating",
        "\U0001f300 Swirling",
        "\U0001f985 Swooping",
        "\U0001f9ec Symbioting",
        "\U0001f52c Synthesizing",
        "\U0001f321\ufe0f Tempering",
        "\U0001f4ad Thinking",
        "\u26a1 Thundering",
        "\U0001f527 Tinkering",
        "\U0001f921 Tomfoolering",
        "\U0001f643 Topsy-turvying",
        "\u2728 Transfiguring",
        "\U0001f9ea Transmuting",
        "\U0001f500 Twisting",
        "\U0001f30a Undulating",
        "\U0001f33a Unfurling",
        "\U0001f9f6 Unravelling",
        "\U0001f60e Vibing",
        "\U0001f986 Waddling",
        "\U0001f6b6 Wandering",
        "\U0001f300 Warping",
        "\U0001f937 Whatchamacalliting",
        "\U0001f300 Whirlpooling",
        "\u2699\ufe0f Whirring",
        "\U0001f9d1\u200d\U0001f373 Whisking",
        "\U0001f974 Wibbling",
        "\U0001f4bc Working",
        "\U0001f920 Wrangling",
        "\U0001f34b Zesting",
        "\u21af Zigzagging",
    ]

    @classmethod
    def _create_thinking_tasks(
        cls,
        emitter: Optional[Callable[[Dict[str, Any]], Awaitable[None]]],
        start_time: float,
        usage_collector: Optional[Dict[str, Any]] = None,
    ) -> List[asyncio.Task[None]]:
        if not emitter:
            return []

        async def _cycle_phrases() -> None:
            phrases = cls._LOADING_PHRASES[:]
            random.shuffle(phrases)
            phrase_idx = 0
            tick = 0
            while True:
                phrase = phrases[phrase_idx % len(phrases)]
                elapsed = perf_counter() - start_time
                suffix = f" {cls._format_elapsed_and_tokens(elapsed, usage_collector)}"
                await emitter(
                    {"type": "status", "data": {"description": f"{phrase}\u2026{suffix}"}}
                )
                tick += 1
                if tick % 5 == 0:
                    phrase_idx += 1
                    if phrase_idx >= len(phrases):
                        random.shuffle(phrases)
                        phrase_idx = 0
                await asyncio.sleep(1.0)

        return [asyncio.create_task(_cycle_phrases())]

    @staticmethod
    def _format_elapsed_and_tokens(
        elapsed: float,
        usage: Optional[Dict[str, Any]] = None,
    ) -> str:
        mins, secs = divmod(int(elapsed), 60)
        parts: List[str] = [f"{mins}m {secs}s" if mins > 0 else f"{secs}s"]
        if usage:
            total_tokens = usage.get("total_tokens")
            if not total_tokens:
                input_t = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
                output_t = (
                    usage.get("output_tokens") or usage.get("completion_tokens") or 0
                )
                total_tokens = input_t + output_t if (input_t or output_t) else 0
            if total_tokens:
                if total_tokens >= 1000:
                    parts.append(f"{total_tokens / 1000:.1f}k tokens")
                else:
                    parts.append(f"{total_tokens} tokens")
        return f"({', '.join(parts)})"

    @staticmethod
    def _cancel_thinking(tasks: List[asyncio.Task[None]]) -> None:
        for t in tasks:
            t.cancel()
        tasks.clear()

    async def _finish_stream(
        self,
        emitter: Optional[Callable[[Dict[str, Any]], Awaitable[None]]],
        thinking_tasks: List[asyncio.Task[None]],
        start_time: float,
        usage: Dict[str, Any],
    ) -> None:
        """Cancel the loading indicator and emit Completed status + completion event.

        Called from inside the streaming methods so the events fire during the
        same __anext__() call that processes the final SSE chunk — before the
        outer generator needs another pull from OpenWebUI.
        """
        self._cancel_thinking(thinking_tasks)
        elapsed = perf_counter() - start_time
        stats = self._format_elapsed_and_tokens(elapsed, usage)
        logger.info(f"Stream finished. usage={usage}, elapsed={elapsed:.1f}s")
        await self._emit_status(emitter, f"Completed {stats}", done=True)
        await self._emit_completion(
            emitter, content="", usage=usage if usage else None, done=True
        )

    # ── URL / logging helpers ────────────────────────────────────────────

    @classmethod
    def pathlib_url_join(cls, base_url: str, path: str) -> str:
        parsed_base = urlparse(base_url)
        full_path = str(PurePosixPath(parsed_base.path) / path.lstrip("/"))
        return urlunparse(
            (
                parsed_base.scheme,
                parsed_base.netloc,
                full_path,
                parsed_base.params,
                parsed_base.query,
                parsed_base.fragment,
            )
        )

    @staticmethod
    def log_httpx_request(request: httpx.Request) -> str:
        return (
            f"HTTPX Request:\n"
            f"- Method: {request.method}\n"
            f"- URL: {request.url}\n"
            f"- Headers: {dict(request.headers)}\n"
            f"- Body: {request.content.decode('utf-8', errors='replace') if request.content else 'No body'}"
        )

    @staticmethod
    def log_response_as_string(response1: httpx.Response) -> str:
        try:
            try:
                response_body = json.dumps(response1.json(), indent=2)
            except (ValueError, json.JSONDecodeError):
                response_body = response1.text[:1000]
        except Exception:
            response_body = "(Unable to decode response body)"
        return (
            f"HTTPX Response Log:\n"
            f"- Timestamp: {datetime.datetime.now().isoformat()}\n"
            f"- Status Code: {response1.status_code}\n"
            f"- URL: {response1.request.url}\n"
            f"- Method: {response1.request.method}\n"
            f"- Response Headers: {json.dumps(dict(response1.headers), indent=2)}\n"
            f"- Response Body: {response_body}\n"
            f"- Response Encoding: {response1.encoding}\n"
            f"- Response Elapsed Time: {response1.elapsed}"
        )

    # ── Header / request helpers ─────────────────────────────────────────

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
        return bool(prompt and prompt.lstrip().startswith("DEBUG:"))

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

    # ── Completions → Responses API body transformation ──────────────────

    @staticmethod
    def _transform_to_responses_body(
        body: Dict[str, Any],
        *,
        store: bool = False,
        previous_response_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        messages: List[Dict[str, Any]] = body.get("messages", [])

        instructions: Optional[str] = None
        for msg in messages:
            if msg.get("role") == "system":
                content = msg.get("content", "")
                if isinstance(content, str):
                    instructions = content
                break

        input_items: List[Dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role")
            raw_content = msg.get("content", "")

            if role == "system":
                continue

            if role == "user":
                content_blocks = raw_content
                if isinstance(content_blocks, str):
                    content_blocks = [{"type": "input_text", "text": content_blocks}]
                elif isinstance(content_blocks, list):
                    transformed: List[Dict[str, Any]] = []
                    for block in content_blocks:
                        if not isinstance(block, dict):
                            continue
                        block_type = block.get("type", "")
                        if block_type == "text":
                            transformed.append(
                                {"type": "input_text", "text": block.get("text", "")}
                            )
                        elif block_type == "image_url":
                            transformed.append(
                                {
                                    "type": "input_image",
                                    "image_url": block.get("image_url", {}).get(
                                        "url", ""
                                    ),
                                }
                            )
                        else:
                            transformed.append(block)
                    content_blocks = transformed
                input_items.append({"role": "user", "content": content_blocks})

            elif role == "assistant":
                if isinstance(raw_content, str) and raw_content:
                    input_items.append(
                        {
                            "role": "assistant",
                            "content": [{"type": "output_text", "text": raw_content}],
                        }
                    )

            elif role == "developer":
                input_items.append({"role": "developer", "content": raw_content})

        responses_payload: Dict[str, Any] = {
            "model": body.get("model", ""),
            "input": input_items,
            "stream": body.get("stream", False),
            "store": store,
        }

        if instructions:
            responses_payload["instructions"] = instructions

        if previous_response_id:
            responses_payload["previous_response_id"] = previous_response_id
            last_user_items: list[Dict[str, Any]] = []
            for item in reversed(input_items):
                if item.get("role") == "user":
                    last_user_items.insert(0, item)
                    break
            if last_user_items:
                responses_payload["input"] = last_user_items

        if "temperature" in body:
            responses_payload["temperature"] = body["temperature"]
        if "top_p" in body:
            responses_payload["top_p"] = body["top_p"]
        if "max_tokens" in body:
            responses_payload["max_output_tokens"] = body["max_tokens"]
        if "max_output_tokens" in body:
            responses_payload["max_output_tokens"] = body["max_output_tokens"]

        effort = body.get("reasoning_effort")
        if effort:
            responses_payload["reasoning"] = {"effort": effort}

        return responses_payload

    # ── SSE parsers ──────────────────────────────────────────────────────

    async def _iter_sse_events(
        self,
        response: httpx.Response,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        buf = bytearray()
        async for chunk in response.aiter_bytes():
            buf.extend(chunk)
            start_idx = 0
            while True:
                newline_idx = buf.find(b"\n", start_idx)
                if newline_idx == -1:
                    break

                line = buf[start_idx:newline_idx].strip()
                start_idx = newline_idx + 1

                if not line or line.startswith(b":"):
                    continue
                if not line.startswith(b"data:"):
                    continue

                data_part = line[5:].strip()

                if data_part == b"[DONE]":
                    return

                try:
                    yield json.loads(data_part.decode("utf-8"))
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Failed to parse SSE data: {data_part!r}, error: {e}"
                    )

            if start_idx > 0:
                del buf[:start_idx]

    async def _stream_chat_completions(
        self,
        response: httpx.Response,
        *,
        emitter: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        thinking_tasks: List[asyncio.Task[None]],
        usage_collector: Dict[str, Any],
        start_time: float,
    ) -> AsyncGenerator[str, None]:
        """Parse Chat Completions streaming response.

        Emits "Completed" status from *inside* this generator so the event
        fires during the same ``__anext__()`` call that processes the final
        SSE chunks — before OpenWebUI needs to pull again.
        """
        first_token_received = False

        async for chunk_json in self._iter_sse_events(response):
            if "usage" in chunk_json and chunk_json["usage"]:
                logger.info(f"Chat Completions usage received: {chunk_json['usage']}")
                self._merge_usage(usage_collector, chunk_json["usage"])

            choices = chunk_json.get("choices")
            if not choices:
                continue

            delta = choices[0].get("delta", {})
            content = delta.get("content")
            if content:
                if not first_token_received:
                    first_token_received = True
                    self._cancel_thinking(thinking_tasks)
                    await self._emit_status(emitter, "Responding\u2026", done=True)
                yield content

        # Stream exhausted — emit completed immediately (same __anext__ call)
        await self._finish_stream(
            emitter, thinking_tasks, start_time, usage_collector
        )

    async def _stream_responses_api(
        self,
        response: httpx.Response,
        *,
        emitter: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        thinking_tasks: List[asyncio.Task[None]],
        chat_id: Optional[str] = None,
        usage_collector: Dict[str, Any],
        start_time: float,
    ) -> AsyncGenerator[str, None]:
        """Parse Responses API streaming events.

        Emits "Completed" status from *inside* this generator so the event
        fires during the same ``__anext__()`` call that processes
        ``response.completed`` — before OpenWebUI needs to pull again.
        """
        first_token_received = False

        async for event in self._iter_sse_events(response):
            etype = event.get("type", "")

            if etype == "response.output_text.delta":
                delta = event.get("delta", "")
                if delta:
                    if not first_token_received:
                        first_token_received = True
                        self._cancel_thinking(thinking_tasks)
                        await self._emit_status(emitter, "Responding\u2026", done=True)
                    yield delta
                continue

            if etype == "response.reasoning_summary_text.done":
                text = (event.get("text") or "").strip()
                if text:
                    await self._emit_status(
                        emitter, f"Reasoning: {text[:200]}", done=True
                    )
                continue

            if etype == "response.output_item.added":
                item = event.get("item", {})
                item_type = item.get("type", "")
                if item_type == "message" and item.get("status") == "in_progress":
                    if not first_token_received:
                        await self._emit_status(emitter, "Responding\u2026")
                elif item_type == "function_call":
                    name = item.get("name", "tool")
                    await self._emit_status(emitter, f"Running {name}\u2026")
                continue

            if etype == "response.output_item.done":
                item = event.get("item", {})
                item_type = item.get("type", "")
                if item_type == "web_search_call":
                    await self._emit_status(emitter, "Search complete", done=True)
                elif item_type == "function_call":
                    name = item.get("name", "tool")
                    await self._emit_status(emitter, f"{name} complete", done=True)
                continue

            if etype == "response.completed":
                final = event.get("response", {})
                rid = final.get("id")
                usage = final.get("usage")
                logger.info(f"Responses API completed - usage: {usage}")
                if chat_id and rid:
                    self._response_id_by_chat[chat_id] = rid
                if usage:
                    self._merge_usage(usage_collector, usage)
                break

        # Stream exhausted — emit completed immediately (same __anext__ call)
        await self._finish_stream(
            emitter, thinking_tasks, start_time, usage_collector
        )

    @staticmethod
    def _merge_usage(total: Dict[str, Any], new: Dict[str, Any]) -> None:
        for k, v in new.items():
            if isinstance(v, dict):
                if k not in total or not isinstance(total[k], dict):
                    total[k] = {}
                Pipe._merge_usage(total[k], v)
            elif isinstance(v, (int, float)):
                total[k] = total.get(k, 0) + v
            elif v is not None:
                total[k] = v

    # ── Main pipe method ─────────────────────────────────────────────────

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
        if not __oauth_token__ or "access_token" not in __oauth_token__:
            await self._emit_error(
                __event_emitter__,
                "Your Auth token has expired. Please logout and login to Aiden"
                " to get a new Auth token.",
            )
            return

        access_token: Optional[str] = __oauth_token__.get("access_token")
        id_token: Optional[str] = __oauth_token__.get("id_token")

        logger.debug(f"pipe:{__name__}")
        logger.debug(f"body: {body}")
        logger.debug(f"__user__: {__user__}")

        if __request__ is None:
            raise ValueError("Request object must be provided.")

        open_api_base_url: Optional[str] = (
            self.valves.OPENAI_API_BASE_URL or self.read_base_url()
        )
        if not open_api_base_url:
            raise RuntimeError(
                "OpenAI API base URL must be set as an environment variable."
            )

        model_id = body.get("model", "")
        if "." in model_id:
            model_id = model_id.split(".", 1)[1]

        api_mode = self.valves.api_mode
        is_responses = api_mode in ("responses_stateless", "responses_stateful")

        if is_responses:
            is_stateful = api_mode == "responses_stateful"
            previous_response_id = (
                self._response_id_by_chat.get(__chat_id__ or "")
                if is_stateful
                else None
            )
            payload = self._transform_to_responses_body(
                {**body, "model": model_id},
                store=is_stateful,
                previous_response_id=previous_response_id,
            )
            url = self.pathlib_url_join(base_url=open_api_base_url, path="responses")
        else:
            payload = {**body, "model": model_id}
            url = self.pathlib_url_join(
                base_url=open_api_base_url, path="chat/completions"
            )

        stream: Optional[bool] = self.valves.stream
        if stream is not None:
            payload["stream"] = stream

        if payload.get("stream"):
            payload.setdefault("stream_options", {})["include_usage"] = True

        is_streaming: bool = bool(payload.get("stream", False))

        headers = self._build_headers(
            request=__request__,
            user=__user__,
            access_token=access_token,
            id_token=id_token,
            session_id=__session_id__,
            chat_id=__chat_id__,
            message_id=__message_id__,
            debug_mode=self._is_debug_request(body),
        )

        for debug_line in self._yield_debug_info(
            user=__user__,
            request=__request__,
            url=url,
            headers=headers,
            payload=payload,
        ):
            yield debug_line

        start_time = perf_counter()
        error_occurred = False
        total_usage: Dict[str, Any] = {}

        # Skip the loading indicator for background tasks (title generation, etc.)
        is_background_task = bool(
            __metadata__ and __metadata__.get("task")
        )

        thinking_tasks: List[asyncio.Task[None]] = []
        if self.valves.enable_status_indicator and is_streaming and not is_background_task:
            thinking_tasks = self._create_thinking_tasks(
                __event_emitter__,
                start_time=start_time,
                usage_collector=total_usage,
            )

        try:
            logger.debug(
                f"Calling {api_mode} url: {url} with payload: {json.dumps(payload)}"
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
                        if response.status_code >= 400:
                            await response.aread()
                            response.raise_for_status()

                        content_type = response.headers.get("content-type", "")
                        if "text/event-stream" in content_type:
                            if is_responses:
                                async for text_chunk in self._stream_responses_api(
                                    response,
                                    emitter=__event_emitter__,
                                    thinking_tasks=thinking_tasks,
                                    chat_id=__chat_id__,
                                    usage_collector=total_usage,
                                    start_time=start_time,
                                ):
                                    yield text_chunk
                            else:
                                async for text_chunk in self._stream_chat_completions(
                                    response,
                                    emitter=__event_emitter__,
                                    thinking_tasks=thinking_tasks,
                                    usage_collector=total_usage,
                                    start_time=start_time,
                                ):
                                    yield text_chunk
                        else:
                            # Non-SSE response from a streaming request
                            self._cancel_thinking(thinking_tasks)
                            await self._emit_status(
                                __event_emitter__, "Responding\u2026", done=True
                            )
                            raw_body = await response.aread()
                            response_text = raw_body.decode("utf-8", errors="replace")
                            try:
                                data = json.loads(response_text)
                                resp_usage = data.get("usage")
                                if resp_usage:
                                    self._merge_usage(total_usage, resp_usage)
                                if is_responses:
                                    text = self._extract_responses_text(data)
                                    rid = data.get("id")
                                    if __chat_id__ and rid:
                                        self._response_id_by_chat[__chat_id__] = rid
                                    yield text if text else json.dumps(data)
                                else:
                                    choices = data.get("choices", [])
                                    if choices:
                                        message = choices[0].get("message", {})
                                        content = message.get("content", "")
                                        yield content if content else json.dumps(data)
                                    else:
                                        yield json.dumps(data)
                            except json.JSONDecodeError:
                                yield response_text
                            await self._finish_stream(
                                __event_emitter__,
                                thinking_tasks,
                                start_time,
                                total_usage,
                            )
                else:
                    self._cancel_thinking(thinking_tasks)
                    response = await client.post(
                        url=url,
                        json=payload,
                        headers=headers,
                        timeout=self.valves.llm_call_timeout_seconds,
                        follow_redirects=True,
                    )
                    response.raise_for_status()
                    data = response.json()
                    resp_usage = data.get("usage")
                    if resp_usage:
                        self._merge_usage(total_usage, resp_usage)
                    if is_responses:
                        text = self._extract_responses_text(data)
                        rid = data.get("id")
                        if __chat_id__ and rid:
                            self._response_id_by_chat[__chat_id__] = rid
                        yield text if text else json.dumps(data)
                    else:
                        yield json.dumps(data)
                    await self._finish_stream(
                        __event_emitter__,
                        thinking_tasks,
                        start_time,
                        total_usage,
                    )

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
            if error_occurred:
                elapsed = perf_counter() - start_time
                stats = self._format_elapsed_and_tokens(elapsed, total_usage)
                await self._emit_status(
                    __event_emitter__, f"Failed {stats}", done=True
                )
                await self._emit_completion(
                    __event_emitter__,
                    content="",
                    usage=total_usage if total_usage else None,
                    done=True,
                )

    # ── Responses API helpers ────────────────────────────────────────────

    @staticmethod
    def _extract_responses_text(data: Dict[str, Any]) -> str:
        parts: List[str] = []
        for item in data.get("output", []):
            if item.get("type") != "message":
                continue
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    parts.append(block.get("text", ""))
        return "".join(parts)

    # ── Models list ──────────────────────────────────────────────────────

    async def get_models(self) -> List[Dict[str, str]]:
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

        default_model_id = self.valves.default_model
        if default_model_id:
            if any(m["id"] == default_model_id for m in self.pipelines or []):
                models = [m for m in models if m["id"] != default_model_id]
                models.insert(0, {"id": default_model_id, "name": default_model_id})

        return models
