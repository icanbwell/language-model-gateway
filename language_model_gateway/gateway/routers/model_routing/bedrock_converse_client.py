"""
Native Bedrock Converse API transport — an alternative to Bedrock Mantle's
OpenAI-compatible endpoint for auth="aws" routes, toggled by
CodingModelRouter._bedrock_transport ("mantle" default / "native").

Kept separate from bedrock_client.py (httpx passthrough + retry helpers for
the Mantle/Anthropic-passthrough paths) and aws_auth.py (SigV4 signing,
credential-error mapping for those same paths) — this module owns the boto3
bedrock-runtime client and the Anthropic/OpenAI <-> Converse format
conversions, which are a distinct concern from either.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

from .bedrock_client import _TRANSIENT_STREAM_ERROR_CODES

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("LLM", logging.INFO))

_CLIENT_CACHE: dict[tuple[str | None, str], Any] = {}
_CLIENT_CACHE_LOCK = threading.Lock()

# Converse's stopReason values that have a direct Anthropic equivalent.
# guardrail_intervened/content_filtered have no Anthropic counterpart —
# they fall through to the "end_turn" default below, matching the
# "no exhaustive enum switch without a default" rule for forward
# compatibility with stop reasons this router doesn't know about yet.
_CONVERSE_TO_ANT_STOP = {
    "end_turn": "end_turn",
    "tool_use": "tool_use",
    "max_tokens": "max_tokens",
    "stop_sequence": "stop_sequence",
}


def _get_bedrock_runtime_client(route: dict[str, Any]) -> Any:
    """Return a cached boto3 bedrock-runtime client for this route's
    (AWS_PROFILE, region) pair. boto3 clients are thread-safe and reusable,
    so one is built per pair, not per request — mirrors the credential
    resolution in aws_auth.py's _sign_bedrock, which also keys off
    AWS_PROFILE and the route's aws_region.
    """
    import boto3

    profile = os.environ.get("AWS_PROFILE")
    region = route.get("aws_region", "us-east-1")
    key = (profile, region)
    if key not in _CLIENT_CACHE:
        with _CLIENT_CACHE_LOCK:
            if key not in _CLIENT_CACHE:
                session = (
                    boto3.Session(profile_name=profile) if profile else boto3.Session()
                )
                _CLIENT_CACHE[key] = session.client(
                    "bedrock-runtime", region_name=region
                )
    return _CLIENT_CACHE[key]


def _is_transient_bedrock_error_code(code: str | None) -> bool:
    """Whether a native Bedrock ClientError's Error.Code is worth retrying
    with backoff — reuses the same exception-name taxonomy already applied
    to Bedrock Mantle's mid-stream errors in bedrock_client.py, since these
    are the same underlying Bedrock exception names either way.
    """
    return code in _TRANSIENT_STREAM_ERROR_CODES


def _openai_to_converse_request(
    oai_body_json: dict[str, Any], model_id: str
) -> dict[str, Any]:
    """Translate an OpenAI-Chat-Completions-shaped request body (as produced
    by message_translator.py's _anthropic_to_openai_request, and already run
    through context-budget enforcement by the time router.py reaches the
    native-Bedrock dispatch branch) into kwargs for boto3's
    bedrock-runtime.converse / .converse_stream.

    Deliberately converts from the OpenAI shape, not the original Anthropic
    request — see the "Deviation from the committed spec" note in this
    plan/module for why: budget enforcement already ran on the OpenAI shape
    upstream of this call, and re-deriving from Anthropic would skip it.
    """
    converse: dict[str, Any] = {"modelId": model_id}

    messages: list[dict[str, Any]] = []
    system: list[dict[str, str]] = []
    pending_tool_results: list[dict[str, Any]] = []

    def _flush_tool_results() -> None:
        if pending_tool_results:
            messages.append({"role": "user", "content": list(pending_tool_results)})
            pending_tool_results.clear()

    for msg in oai_body_json.get("messages", []):
        role = msg.get("role")
        if role == "system":
            system.append({"text": msg.get("content") or ""})
            continue
        if role == "tool":
            pending_tool_results.append(
                {
                    "toolResult": {
                        "toolUseId": msg.get("tool_call_id", ""),
                        "content": [{"text": msg.get("content") or ""}],
                    }
                }
            )
            continue
        _flush_tool_results()
        if role == "assistant":
            content: list[dict[str, Any]] = []
            if text := msg.get("content"):
                content.append({"text": text})
            for tc in msg.get("tool_calls") or []:
                fn = tc.get("function", {})
                try:
                    tool_input = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    tool_input = {}
                content.append(
                    {
                        "toolUse": {
                            "toolUseId": tc.get("id", ""),
                            "name": fn.get("name", ""),
                            "input": tool_input,
                        }
                    }
                )
            messages.append({"role": "assistant", "content": content})
        elif role == "user":
            content_field = msg.get("content")
            if isinstance(content_field, str):
                messages.append({"role": "user", "content": [{"text": content_field}]})
            elif isinstance(content_field, list):
                blocks: list[dict[str, Any]] = []
                for block in content_field:
                    block_type = block.get("type")
                    if block_type == "text":
                        blocks.append({"text": block.get("text", "")})
                    elif block_type == "image_url":
                        logger.warning(
                            "[bedrock-converse] dropping image content block — "
                            "native Bedrock transport does not support image "
                            "input yet"
                        )
                    # Unknown block types are silently skipped, not raised —
                    # forward-compatible with new Anthropic/OpenAI content
                    # block types this router doesn't know about yet.
                messages.append({"role": "user", "content": blocks})
    _flush_tool_results()

    converse["messages"] = messages
    if system:
        converse["system"] = system

    inference_config: dict[str, Any] = {}
    if "max_tokens" in oai_body_json:
        inference_config["maxTokens"] = oai_body_json["max_tokens"]
    if "temperature" in oai_body_json:
        inference_config["temperature"] = oai_body_json["temperature"]
    if "top_p" in oai_body_json:
        inference_config["topP"] = oai_body_json["top_p"]
    if inference_config:
        converse["inferenceConfig"] = inference_config

    tool_choice = oai_body_json.get("tool_choice")
    # tool_choice=="none" means the model must not use any tools. Bedrock Converse
    # has no explicit "disable tools" toolChoice value, so we omit toolConfig
    # entirely — if the model isn't told about any tools, it can't call one.
    if tool_choice != "none" and (tools := oai_body_json.get("tools")):
        tool_config: dict[str, Any] = {
            "tools": [
                {
                    "toolSpec": {
                        "name": t["function"]["name"],
                        "description": t["function"].get("description", ""),
                        "inputSchema": {"json": t["function"].get("parameters", {})},
                    }
                }
                for t in tools
            ]
        }
        if tool_choice == "auto":
            tool_config["toolChoice"] = {"auto": {}}
        elif tool_choice == "required":
            tool_config["toolChoice"] = {"any": {}}
        elif isinstance(tool_choice, dict):
            tool_config["toolChoice"] = {
                "tool": {"name": tool_choice.get("function", {}).get("name", "")}
            }
        converse["toolConfig"] = tool_config

    return converse


def _converse_response_to_anthropic(
    resp: dict[str, Any], msg_id: str, upstream_model: str
) -> dict[str, Any]:
    """Translate a non-streaming Bedrock Converse response to Anthropic
    Messages format — the Converse-API counterpart to
    message_translator.py's _openai_to_anthropic_response.
    """
    content: list[dict[str, Any]] = []
    message = resp.get("output", {}).get("message", {})
    for block in message.get("content", []):
        if "text" in block:
            content.append({"type": "text", "text": block["text"]})
        elif "toolUse" in block:
            tool_use = block["toolUse"]
            content.append(
                {
                    "type": "tool_use",
                    "id": tool_use.get("toolUseId", ""),
                    "name": tool_use.get("name", ""),
                    "input": tool_use.get("input", {}),
                }
            )

    stop_reason = _CONVERSE_TO_ANT_STOP.get(resp.get("stopReason", ""), "end_turn")
    usage = resp.get("usage", {})

    return {
        "id": msg_id,
        "type": "message",
        "role": "assistant",
        "content": content,
        "model": upstream_model,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("inputTokens", 0),
            "output_tokens": usage.get("outputTokens", 0),
        },
    }
