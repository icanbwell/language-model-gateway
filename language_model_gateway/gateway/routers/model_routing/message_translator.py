from __future__ import annotations

import json
import os
import re
from typing import Any

from .constants import _OAI_TO_ANT_STOP

# Environment variable to control whether to append cost savings info to response
_COST_SAVINGS_ENABLED = os.environ.get("ENABLE_COST_SAVINGS_INFO", "false").lower() in (
    "true",
    "1",
    "yes",
)


def _anthropic_content_to_text(content: str | list[Any]) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content if b.get("type") == "text")


def _estimate_input_tokens(body_json: dict[str, Any]) -> int:
    """Estimate input token count from an Anthropic request body (4 chars ≈ 1 token)."""
    total_chars = 0
    if system := body_json.get("system"):
        total_chars += len(_anthropic_content_to_text(system))
    for msg in body_json.get("messages", []):
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for block in content:
                btype = block.get("type")
                if btype == "text":
                    total_chars += len(block.get("text", ""))
                elif btype == "tool_use":
                    total_chars += len(block.get("name", ""))
                    inp = block.get("input")
                    if inp:
                        total_chars += len(json.dumps(inp))
                elif btype == "tool_result":
                    result_content = block.get("content", "")
                    if isinstance(result_content, str):
                        total_chars += len(result_content)
                    elif isinstance(result_content, list):
                        for rb in result_content:
                            if rb.get("type") == "text":
                                total_chars += len(rb.get("text", ""))
    for tool in body_json.get("tools", []):
        total_chars += len(tool.get("name", ""))
        total_chars += len(tool.get("description", ""))
        schema = tool.get("input_schema") or tool.get("parameters") or {}
        if schema:
            total_chars += len(json.dumps(schema))
    return (total_chars + 3) // 4


def _convert_user_content(blocks: list[Any]) -> str | list[Any]:
    text_only = all(b.get("type") == "text" for b in blocks)
    if text_only:
        return "\n".join(b.get("text", "") for b in blocks)
    result: list[Any] = []
    for block in blocks:
        btype = block.get("type")
        if btype == "text":
            result.append({"type": "text", "text": block.get("text", "")})
        elif btype == "image":
            src = block.get("source", {})
            if src.get("type") == "base64":
                url = f"data:{src.get('media_type', 'image/jpeg')};base64,{src.get('data', '')}"
            else:
                url = src.get("url", "")
            result.append({"type": "image_url", "image_url": {"url": url}})
    return result


def _anthropic_to_openai_request(body_json: dict[str, Any]) -> dict[str, Any]:
    """Translate an Anthropic Messages API request body to OpenAI Chat Completions format."""
    oai: dict[str, Any] = {"model": body_json["model"]}
    for field in ("stream", "temperature", "top_p", "max_tokens"):
        if field in body_json:
            oai[field] = body_json[field]

    messages: list[Any] = []
    if system := body_json.get("system"):
        messages.append(
            {"role": "system", "content": _anthropic_content_to_text(system)}
        )

    for msg in body_json.get("messages", []):
        role = msg["role"]
        content = msg["content"]
        if role == "assistant":
            if isinstance(content, list):
                text_parts: list[str] = []
                tool_calls: list[dict[str, Any]] = []
                for block in content:
                    btype = block.get("type")
                    if btype == "text":
                        text_parts.append(block.get("text", ""))
                    elif btype == "tool_use":
                        tool_calls.append(
                            {
                                "id": block.get("id", f"call_{len(tool_calls)}"),
                                "type": "function",
                                "function": {
                                    "name": block.get("name", ""),
                                    "arguments": json.dumps(block.get("input", {})),
                                },
                            }
                        )
                oai_msg: dict[str, Any] = {"role": "assistant"}
                if text_parts:
                    oai_msg["content"] = "\n".join(text_parts)
                if tool_calls:
                    oai_msg["tool_calls"] = tool_calls
                messages.append(oai_msg)
            else:
                messages.append({"role": "assistant", "content": content or ""})
        elif role == "user":
            if isinstance(content, list):
                pending: list[Any] = []
                for block in content:
                    if block.get("type") == "tool_result":
                        if pending:
                            messages.append(
                                {
                                    "role": "user",
                                    "content": _convert_user_content(pending),
                                }
                            )
                            pending = []
                        result_content = block.get("content", "")
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": block.get("tool_use_id", ""),
                                "content": (
                                    _anthropic_content_to_text(result_content)
                                    if isinstance(result_content, list)
                                    else str(result_content or "")
                                ),
                            }
                        )
                    else:
                        pending.append(block)
                if pending:
                    messages.append(
                        {"role": "user", "content": _convert_user_content(pending)}
                    )
            else:
                messages.append({"role": "user", "content": content or ""})

    oai["messages"] = messages

    if tools := body_json.get("tools"):
        oai["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {}),
                },
            }
            for t in tools
        ]

    if tc := body_json.get("tool_choice"):
        tc_type = tc.get("type")
        if tc_type == "auto":
            oai["tool_choice"] = "auto"
        elif tc_type == "any":
            oai["tool_choice"] = "required"
        elif tc_type == "none":
            oai["tool_choice"] = "none"
        elif tc_type == "tool":
            oai["tool_choice"] = {
                "type": "function",
                "function": {"name": tc.get("name", "")},
            }

    return oai


def _openai_to_anthropic_response(
    resp_json: dict[str, Any], msg_id: str, upstream_model: str
) -> dict[str, Any]:
    """Translate a non-streaming OpenAI Chat Completions response to Anthropic format."""
    usage = resp_json.get("usage", {})
    content: list[Any] = []
    stop_reason = "end_turn"
    choices = resp_json.get("choices", [])
    if choices:
        choice = choices[0]
        message = choice.get("message", {})
        stop_reason = _OAI_TO_ANT_STOP.get(
            choice.get("finish_reason", "stop"), "end_turn"
        )
        if text := message.get("content"):
            text = (
                re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
                .strip("\n")
                .strip()
            )
            if text:
                content.append({"type": "text", "text": text})
        for tc in message.get("tool_calls") or []:
            fn = tc.get("function", {})
            try:
                input_data = json.loads(fn.get("arguments", "{}"))
            except json.JSONDecodeError:
                input_data = {}
            content.append(
                {
                    "type": "tool_use",
                    "id": tc.get("id", f"toolu_{len(content):04x}"),
                    "name": fn.get("name", ""),
                    "input": input_data,
                }
            )
    response = {
        "id": msg_id,
        "type": "message",
        "role": "assistant",
        "content": content,
        "model": upstream_model,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
    }

    # Optionally append cost savings info to the response content
    if _COST_SAVINGS_ENABLED and content:
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost_info = (
            f"\n\n—\n*Cost: {input_tokens} input + {output_tokens} output tokens. "
            "Routing decision optimized for cost/quality balance.*"
        )
        # Prepend cost info so it appears at the top in Claude Code
        content[0]["text"] = content[0]["text"] + cost_info

    return response
