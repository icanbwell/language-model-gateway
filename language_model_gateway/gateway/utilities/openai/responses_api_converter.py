from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)


def convert_responses_api_output_to_message(
    output_item: Mapping[str, Any],
) -> Optional[BaseMessage]:
    """Convert a single output item from OpenAI Responses API to a LangChain message.

    Args:
        output_item: A single output item from the Responses API output list.

    Returns:
        A LangChain BaseMessage object, or None if the output type is not a message.

    Raises:
        ValueError: If the output item type is not supported.
    """
    output_type = output_item.get("type")

    if output_type == "message":
        # Standard message output
        role = output_item.get("role")
        content_list = output_item.get("content", [])

        # Extract text content from content array
        text_content = ""
        for content_item in content_list:
            if content_item.get("type") in ("output_text", "input_text"):
                text_content += content_item.get("text", "")

        # Convert based on role
        if role == "user":
            return HumanMessage(content=text_content)
        elif role == "assistant":
            return AIMessage(content=text_content or "")
        elif role == "system":
            return SystemMessage(content=text_content)
        else:
            # For any other role, we could use ChatMessage but it's not in the imports
            # For now, treat as AIMessage with role in metadata
            return AIMessage(
                content=text_content, additional_kwargs={"role": role} if role else {}
            )

    elif output_type == "function_call":
        # Function call output - convert to AIMessage with function_call in additional_kwargs
        function_name = output_item.get("name", "")
        arguments = output_item.get("arguments", {})
        call_id = output_item.get("call_id")

        additional_kwargs: Dict[str, Any] = {
            "function_call": {
                "name": function_name,
                "arguments": arguments,
            }
        }
        if call_id:
            additional_kwargs["function_call"]["id"] = call_id

        return AIMessage(content="", additional_kwargs=additional_kwargs)

    elif output_type == "function_call_output":
        # Function call result - convert to FunctionMessage
        call_id = output_item.get("call_id")
        output_content = output_item.get("output", "")

        # FunctionMessage requires a name, try to extract from context
        # In Responses API, the name might not be directly available
        # We'll use call_id as a fallback
        return ToolMessage(
            content=output_content, tool_call_id=call_id or "", additional_kwargs={}
        )

    # For other types (image_generation_call, mcp_approval_request, etc.)
    # we return None as they don't map directly to standard LangChain messages
    return None


def convert_responses_api_to_messages(response: Mapping[str, Any]) -> List[BaseMessage]:
    """Convert an OpenAI Responses API response to a list of LangChain messages.

    Args:
        response: The complete response object from the Responses API.

    Returns:
        A list of LangChain BaseMessage objects.

    Examples:
        >>> response = {
        ...     "output": [
        ...         {
        ...             "type": "message",
        ...             "role": "assistant",
        ...             "content": [{"type": "output_text", "text": "Hello!"}]
        ...         }
        ...     ]
        ... }
        >>> messages = convert_responses_api_to_messages(response)
        >>> len(messages)
        1
        >>> isinstance(messages[0], AIMessage)
        True
    """
    output_items = response.get("output", [])
    messages: List[BaseMessage] = []

    for output_item in output_items:
        message = convert_responses_api_output_to_message(output_item)
        if message is not None:
            messages.append(message)

    return messages


def convert_responses_api_to_single_message(
    response: Mapping[str, Any],
) -> BaseMessage:
    """Convert a single output item from the OpenAI Responses API to a LangChain message.

    Args:
        response: A single output item from the Responses API output field.

    Returns:
        A single LangChain BaseMessage (typically AIMessage).

    Raises:
        ValueError: If no valid message output is found in the output_item.
    """
    output_type = response.get("type")
    combined_content = ""
    combined_kwargs: Dict[str, Any] = {}
    function_calls_list: List[Dict[str, Any]] = []

    if output_type == "message" and response.get("role") == "assistant":
        content_list = response.get("content", [])
        for content_item in content_list:
            if content_item.get("type") in ("output_text", "input_text"):
                combined_content += content_item.get("text", "")

    elif output_type == "function_call":
        function_calls_list.append(
            {
                "id": response.get("call_id"),
                "name": response.get("name"),
                "arguments": response.get("arguments", {}),
                "type": "function",
            }
        )

    elif output_type == "easy_input_message_param":
        # Handle EasyInputMessageParam type
        content = response.get("content", "")
        params = response.get("params", {})
        if content:
            combined_content += content
        if params:
            combined_kwargs["easy_input_params"] = params

    # Add function calls to additional_kwargs if present
    if function_calls_list:
        combined_kwargs["tool_calls"] = function_calls_list
        if not combined_content:
            combined_content = ""

    if not combined_content and not combined_kwargs:
        raise ValueError("No valid message content found in output_item")

    return AIMessage(content=combined_content, additional_kwargs=combined_kwargs)


def convert_responses_api_to_single_message_from_response(
    response: Mapping[str, Any],
) -> BaseMessage:
    """Backward-compatible wrapper to accept the full response dict and use the first output item."""
    output_items = response.get("output", [])
    if not output_items:
        raise ValueError("No output items found in response")
    return convert_responses_api_to_single_message(output_items[0])


def extract_output_text(response: Mapping[str, Any]) -> str:
    """Extract the output text from a Responses API response.

    This is a convenience function that extracts just the text content
    from the response, similar to response.output_text in the API.

    Args:
        response: The complete response object from the Responses API.

    Returns:
        The extracted text content as a string.
    """
    # First check if output_text is directly available
    if "output_text" in response:
        return response["output_text"] or ""

    # Otherwise, extract from output items
    output_items = response.get("output", [])
    text_parts: List[str] = []

    for output_item in output_items:
        if output_item.get("type") == "message":
            content_list = output_item.get("content", [])
            for content_item in content_list:
                if content_item.get("type") in ("output_text", "input_text"):
                    text = content_item.get("text", "")
                    if text:
                        text_parts.append(text)

    return "".join(text_parts)
