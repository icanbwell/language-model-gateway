"""Utilities for Server-Sent Events (SSE) streaming."""

import json
from typing import Any


def format_sse(event: dict[str, Any]) -> str:
    """
    Format an event as a Server-Sent Event.

    Args:
        event: The event data to format

    Returns:
        SSE-formatted string ready to send to client
    """
    return f"data: {json.dumps(event)}\n\n"


def format_chat_completion_chunk_sse(chunk_data: dict[str, Any]) -> str:
    """
    Format a chat completion chunk as an SSE event.

    Args:
        chunk_data: The chunk data to format

    Returns:
        SSE-formatted string
    """
    return format_sse(chunk_data)


def format_done_sse() -> str:
    """
    Format the final [DONE] message for chat completion streaming.

    Returns:
        SSE-formatted done message
    """
    return "data: [DONE]\n\n"
