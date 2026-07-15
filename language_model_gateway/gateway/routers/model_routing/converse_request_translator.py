"""
Translation between the OpenAI-Chat-Completions request/response shape used
internally by CodingModelRouter and boto3's Bedrock Converse API shape.

Split out of bedrock_converse_client.py, which now owns only client
lifecycle/caching and native-Bedrock error-code classification. Streaming
adaptation lives in converse_stream_adapter.py.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

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

# Bedrock Converse enforces this as a hard limit on toolSpec.name / toolUse.name.
# MCP-prefixed tool names (e.g. mcp__claude_ai_Intuit_QuickBooks__qbo_accounting_
# get_balance_sheet) routinely exceed it, which otherwise fails the whole
# request with a ValidationException rather than just dropping that tool.
_MAX_BEDROCK_TOOL_NAME_LEN = 64


def _safe_bedrock_tool_name(name: str) -> str:
    """Shorten a tool name to fit Bedrock's limit, deterministically — the
    same original name always produces the same safe name across turns, and
    a hash suffix keeps two long names sharing a common prefix from
    colliding after truncation.
    """
    if len(name) <= _MAX_BEDROCK_TOOL_NAME_LEN:
        return name
    digest = hashlib.sha1(name.encode(), usedforsecurity=False).hexdigest()[:8]
    prefix_len = _MAX_BEDROCK_TOOL_NAME_LEN - len(digest) - 1
    return f"{name[:prefix_len]}_{digest}"


def _openai_to_converse_request(
    oai_body_json: dict[str, Any], model_id: str
) -> tuple[dict[str, Any], dict[str, str]]:
    """Translate an OpenAI-Chat-Completions-shaped request body (as produced
    by message_translator.py's _anthropic_to_openai_request, and already run
    through context-budget enforcement by the time router.py reaches the
    native-Bedrock dispatch branch) into kwargs for boto3's
    bedrock-runtime.converse / .converse_stream.

    Deliberately converts from the OpenAI shape, not the original Anthropic
    request — see the "Deviation from the committed spec" note in this
    plan/module for why: budget enforcement already ran on the OpenAI shape
    upstream of this call, and re-deriving from Anthropic would skip it.

    Also returns a safe-name -> original-name map for any tool names
    shortened by _safe_bedrock_tool_name, so the response translators can
    restore the original name before it reaches the client.
    """
    converse: dict[str, Any] = {"modelId": model_id}
    tool_name_map: dict[str, str] = {}

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
                original_name = fn.get("name", "")
                safe_name = _safe_bedrock_tool_name(original_name)
                tool_name_map[safe_name] = original_name
                content.append(
                    {
                        "toolUse": {
                            "toolUseId": tc.get("id", ""),
                            "name": safe_name,
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
        tools_list: list[dict[str, Any]] = []
        for t in tools:
            original_name = t["function"]["name"]
            safe_name = _safe_bedrock_tool_name(original_name)
            tool_name_map[safe_name] = original_name
            tools_list.append(
                {
                    "toolSpec": {
                        "name": safe_name,
                        "description": t["function"].get("description", ""),
                        "inputSchema": {"json": t["function"].get("parameters", {})},
                    }
                }
            )
        tool_config: dict[str, Any] = {"tools": tools_list}
        if tool_choice == "auto":
            tool_config["toolChoice"] = {"auto": {}}
        elif tool_choice == "required":
            tool_config["toolChoice"] = {"any": {}}
        elif isinstance(tool_choice, dict):
            chosen_name = tool_choice.get("function", {}).get("name", "")
            tool_config["toolChoice"] = {
                "tool": {"name": _safe_bedrock_tool_name(chosen_name)}
            }
        converse["toolConfig"] = tool_config

    if chat_template_kwargs := oai_body_json.get("chat_template_kwargs"):
        # Converse's mechanism for model-specific extra parameters — carries
        # e.g. the Qwen `enable_thinking` toggle through on this transport too,
        # so it isn't silently dropped when native is the resolved transport.
        converse["additionalModelRequestFields"] = chat_template_kwargs

    return converse, tool_name_map


def _converse_response_to_anthropic(
    resp: dict[str, Any],
    msg_id: str,
    upstream_model: str,
    tool_name_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Translate a non-streaming Bedrock Converse response to Anthropic
    Messages format — the Converse-API counterpart to
    message_translator.py's _openai_to_anthropic_response.

    tool_name_map (from _openai_to_converse_request) restores any tool name
    Bedrock's 64-character limit forced us to shorten before sending, so the
    client sees the same name it originally declared.
    """
    content: list[dict[str, Any]] = []
    message = resp.get("output", {}).get("message", {})
    for block in message.get("content", []):
        if "text" in block:
            content.append({"type": "text", "text": block["text"]})
        elif "toolUse" in block:
            tool_use = block["toolUse"]
            safe_name = tool_use.get("name", "")
            content.append(
                {
                    "type": "tool_use",
                    "id": tool_use.get("toolUseId", ""),
                    "name": (tool_name_map or {}).get(safe_name, safe_name),
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
        "usage": _converse_usage_to_anthropic(usage),
    }


def _converse_usage_to_anthropic(usage: dict[str, Any]) -> dict[str, int]:
    """Map a Bedrock Converse TokenUsage object onto Anthropic's usage
    shape, always including cache_creation_input_tokens/
    cache_read_input_tokens (defaulting to 0) rather than omitting them —
    clients that derive context-window usage from these fields (e.g.
    Claude Code, see anthropics/claude-code#13385) treat a missing field
    the same as a broken one, not as "no caching happened".
    """
    return {
        "input_tokens": usage.get("inputTokens", 0),
        "output_tokens": usage.get("outputTokens", 0),
        "cache_creation_input_tokens": usage.get("cacheWriteInputTokens", 0),
        "cache_read_input_tokens": usage.get("cacheReadInputTokens", 0),
    }
