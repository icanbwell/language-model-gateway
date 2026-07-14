"""
Tests for converse_request_translator.py's OpenAI <-> Bedrock Converse
request/response translation helpers.
"""

from __future__ import annotations

from language_model_gateway.gateway.routers.model_routing.converse_request_translator import (
    _MAX_BEDROCK_TOOL_NAME_LEN,
    _converse_response_to_anthropic,
    _openai_to_converse_request,
    _safe_bedrock_tool_name,
)


class TestOpenaiToConverseRequest:
    def test_plain_text_conversation(self) -> None:
        oai_body = {
            "model": "qwen.qwen3-coder-next",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 1024,
        }
        result, _ = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["modelId"] == "qwen.qwen3-coder-next"
        assert result["messages"] == [{"role": "user", "content": [{"text": "Hello"}]}]
        assert result["inferenceConfig"] == {"maxTokens": 1024}
        assert "system" not in result
        assert "toolConfig" not in result

    def test_system_prompt_becomes_system_field(self) -> None:
        oai_body = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hi"},
            ],
        }
        result, _ = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["system"] == [{"text": "You are a helpful assistant."}]
        assert result["messages"] == [{"role": "user", "content": [{"text": "Hi"}]}]

    def test_assistant_tool_call_becomes_tool_use_block(self) -> None:
        oai_body = {
            "messages": [
                {"role": "user", "content": "What's the weather?"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city": "Boston"}',
                            },
                        }
                    ],
                },
            ],
        }
        result, _ = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assistant_msg = result["messages"][1]
        assert assistant_msg["role"] == "assistant"
        assert assistant_msg["content"] == [
            {
                "toolUse": {
                    "toolUseId": "call_1",
                    "name": "get_weather",
                    "input": {"city": "Boston"},
                }
            }
        ]

    def test_tool_result_becomes_user_turn_tool_result_block(self) -> None:
        oai_body = {
            "messages": [
                {"role": "user", "content": "What's the weather?"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "get_weather", "arguments": "{}"},
                        }
                    ],
                },
                {"role": "tool", "tool_call_id": "call_1", "content": "72F, sunny"},
            ],
        }
        result, _ = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        tool_result_msg = result["messages"][2]
        assert tool_result_msg == {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "call_1",
                        "content": [{"text": "72F, sunny"}],
                    }
                }
            ],
        }

    def test_tools_and_tool_choice_become_tool_config(self) -> None:
        oai_body = {
            "messages": [{"role": "user", "content": "Hi"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get current weather",
                        "parameters": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                        },
                    },
                }
            ],
            "tool_choice": "auto",
        }
        result, _ = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["toolConfig"]["tools"] == [
            {
                "toolSpec": {
                    "name": "get_weather",
                    "description": "Get current weather",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                        }
                    },
                }
            }
        ]
        assert result["toolConfig"]["toolChoice"] == {"auto": {}}

    def test_specific_tool_choice_maps_to_named_tool(self) -> None:
        oai_body = {
            "messages": [{"role": "user", "content": "Hi"}],
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "get_weather", "parameters": {}},
                }
            ],
            "tool_choice": {"type": "function", "function": {"name": "get_weather"}},
        }
        result, _ = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["toolConfig"]["toolChoice"] == {"tool": {"name": "get_weather"}}

    def test_multi_turn_conversation_preserves_order(self) -> None:
        oai_body = {
            "messages": [
                {"role": "user", "content": "First question"},
                {"role": "assistant", "content": "First answer"},
                {"role": "user", "content": "Second question"},
            ],
        }
        result, _ = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert [m["role"] for m in result["messages"]] == ["user", "assistant", "user"]
        assert result["messages"][0]["content"] == [{"text": "First question"}]
        assert result["messages"][1]["content"] == [{"text": "First answer"}]
        assert result["messages"][2]["content"] == [{"text": "Second question"}]

    def test_image_url_content_block_is_dropped_not_crashed(self) -> None:
        oai_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/jpeg;base64,abc123"},
                        },
                    ],
                }
            ],
        }
        result, _ = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["messages"][0]["content"] == [{"text": "What's in this image?"}]

    def test_temperature_and_top_p_map_to_inference_config(self) -> None:
        oai_body = {
            "messages": [{"role": "user", "content": "Hi"}],
            "temperature": 0.7,
            "top_p": 0.9,
        }
        result, _ = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert result["inferenceConfig"] == {"temperature": 0.7, "topP": 0.9}

    def test_tool_choice_none_omits_tool_config_entirely(self) -> None:
        oai_body = {
            "messages": [{"role": "user", "content": "Hi"}],
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "get_weather", "parameters": {}},
                }
            ],
            "tool_choice": "none",
        }
        result, _ = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert "toolConfig" not in result

    def test_tool_choice_none_without_tools_still_omits_tool_config(self) -> None:
        oai_body = {
            "messages": [{"role": "user", "content": "Hi"}],
            "tool_choice": "none",
        }
        result, _ = _openai_to_converse_request(oai_body, "qwen.qwen3-coder-next")
        assert "toolConfig" not in result

    def test_long_tool_name_is_shortened_and_mapped_back(self) -> None:
        long_name = "mcp__claude_ai_Intuit_QuickBooks__qbo_accounting_get_balance_sheet"
        oai_body = {
            "messages": [{"role": "user", "content": "Hi"}],
            "tools": [
                {
                    "type": "function",
                    "function": {"name": long_name, "parameters": {}},
                }
            ],
            "tool_choice": "auto",
        }
        result, tool_name_map = _openai_to_converse_request(
            oai_body, "qwen.qwen3-coder-next"
        )
        safe_name = result["toolConfig"]["tools"][0]["toolSpec"]["name"]
        assert len(safe_name) <= _MAX_BEDROCK_TOOL_NAME_LEN
        assert tool_name_map[safe_name] == long_name

    def test_specific_tool_choice_with_long_name_maps_to_safe_name(self) -> None:
        long_name = (
            "mcp__claude_ai_Intuit_QuickBooks__qbo_accounting_get_product_service_list"
        )
        oai_body = {
            "messages": [{"role": "user", "content": "Hi"}],
            "tools": [
                {
                    "type": "function",
                    "function": {"name": long_name, "parameters": {}},
                }
            ],
            "tool_choice": {"type": "function", "function": {"name": long_name}},
        }
        result, tool_name_map = _openai_to_converse_request(
            oai_body, "qwen.qwen3-coder-next"
        )
        chosen_name = result["toolConfig"]["toolChoice"]["tool"]["name"]
        assert len(chosen_name) <= _MAX_BEDROCK_TOOL_NAME_LEN
        assert tool_name_map[chosen_name] == long_name

    def test_replayed_assistant_tool_call_with_long_name_uses_safe_name(self) -> None:
        long_name = "mcp__claude_ai_Intuit_QuickBooks__qbo_accounting_get_balance_sheet"
        oai_body = {
            "messages": [
                {"role": "user", "content": "What's my balance?"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": long_name, "arguments": "{}"},
                        }
                    ],
                },
            ],
        }
        result, tool_name_map = _openai_to_converse_request(
            oai_body, "qwen.qwen3-coder-next"
        )
        safe_name = result["messages"][1]["content"][0]["toolUse"]["name"]
        assert len(safe_name) <= _MAX_BEDROCK_TOOL_NAME_LEN
        assert tool_name_map[safe_name] == long_name


class TestSafeBedrockToolName:
    def test_short_name_passes_through_unchanged(self) -> None:
        assert _safe_bedrock_tool_name("get_weather") == "get_weather"

    def test_name_at_exact_limit_passes_through_unchanged(self) -> None:
        name = "a" * _MAX_BEDROCK_TOOL_NAME_LEN
        assert _safe_bedrock_tool_name(name) == name

    def test_long_name_is_shortened_to_limit(self) -> None:
        long_name = "mcp__claude_ai_Intuit_QuickBooks__qbo_accounting_get_balance_sheet"
        safe_name = _safe_bedrock_tool_name(long_name)
        assert len(safe_name) <= _MAX_BEDROCK_TOOL_NAME_LEN

    def test_same_long_name_maps_deterministically(self) -> None:
        long_name = "mcp__claude_ai_Intuit_QuickBooks__qbo_accounting_get_balance_sheet"
        assert _safe_bedrock_tool_name(long_name) == _safe_bedrock_tool_name(long_name)

    def test_different_long_names_sharing_a_prefix_dont_collide(self) -> None:
        name_a = "mcp__claude_ai_Intuit_QuickBooks__qbo_accounting_get_balance_sheet"
        name_b = (
            "mcp__claude_ai_Intuit_QuickBooks__qbo_accounting_get_product_service_list"
        )
        assert _safe_bedrock_tool_name(name_a) != _safe_bedrock_tool_name(name_b)


class TestConverseResponseToAnthropic:
    def test_plain_text_response(self) -> None:
        resp = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "Hello there"}],
                }
            },
            "stopReason": "end_turn",
            "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
        }
        result = _converse_response_to_anthropic(
            resp, "msg_abc", "qwen.qwen3-coder-next"
        )
        assert result["id"] == "msg_abc"
        assert result["type"] == "message"
        assert result["role"] == "assistant"
        assert result["content"] == [{"type": "text", "text": "Hello there"}]
        assert result["model"] == "qwen.qwen3-coder-next"
        assert result["stop_reason"] == "end_turn"
        assert result["stop_sequence"] is None
        assert result["usage"] == {
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }

    def test_tool_use_response(self) -> None:
        resp = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "tooluse_1",
                                "name": "get_weather",
                                "input": {"city": "Boston"},
                            }
                        }
                    ],
                }
            },
            "stopReason": "tool_use",
            "usage": {"inputTokens": 20, "outputTokens": 8, "totalTokens": 28},
        }
        result = _converse_response_to_anthropic(
            resp, "msg_abc", "qwen.qwen3-coder-next"
        )
        assert result["content"] == [
            {
                "type": "tool_use",
                "id": "tooluse_1",
                "name": "get_weather",
                "input": {"city": "Boston"},
            }
        ]
        assert result["stop_reason"] == "tool_use"

    def test_tool_use_response_restores_original_long_name(self) -> None:
        resp = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "tooluse_1",
                                "name": "safe_name_123",
                                "input": {},
                            }
                        }
                    ],
                }
            },
            "stopReason": "tool_use",
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
        }
        result = _converse_response_to_anthropic(
            resp,
            "msg_abc",
            "qwen.qwen3-coder-next",
            {"safe_name_123": "mcp__claude_ai_Intuit_QuickBooks__original_name"},
        )
        assert result["content"][0]["name"] == (
            "mcp__claude_ai_Intuit_QuickBooks__original_name"
        )

    def test_mixed_text_and_tool_use_content(self) -> None:
        resp = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {"text": "Let me check that for you."},
                        {
                            "toolUse": {
                                "toolUseId": "tooluse_1",
                                "name": "get_weather",
                                "input": {},
                            }
                        },
                    ],
                }
            },
            "stopReason": "tool_use",
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
        }
        result = _converse_response_to_anthropic(
            resp, "msg_abc", "qwen.qwen3-coder-next"
        )
        assert result["content"] == [
            {"type": "text", "text": "Let me check that for you."},
            {"type": "tool_use", "id": "tooluse_1", "name": "get_weather", "input": {}},
        ]

    def test_max_tokens_stop_reason_maps_directly(self) -> None:
        resp = {
            "output": {"message": {"role": "assistant", "content": [{"text": "..."}]}},
            "stopReason": "max_tokens",
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
        }
        result = _converse_response_to_anthropic(
            resp, "msg_abc", "qwen.qwen3-coder-next"
        )
        assert result["stop_reason"] == "max_tokens"

    def test_unknown_stop_reason_defaults_to_end_turn(self) -> None:
        resp = {
            "output": {"message": {"role": "assistant", "content": [{"text": "..."}]}},
            "stopReason": "guardrail_intervened",
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
        }
        result = _converse_response_to_anthropic(
            resp, "msg_abc", "qwen.qwen3-coder-next"
        )
        assert result["stop_reason"] == "end_turn"

    def test_missing_usage_defaults_to_zero(self) -> None:
        resp = {
            "output": {"message": {"role": "assistant", "content": [{"text": "hi"}]}},
            "stopReason": "end_turn",
        }
        result = _converse_response_to_anthropic(
            resp, "msg_abc", "qwen.qwen3-coder-next"
        )
        assert result["usage"] == {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }

    def test_cache_tokens_are_mapped_from_bedrock_field_names(self) -> None:
        """Bedrock Converse's cacheReadInputTokens/cacheWriteInputTokens must
        surface as Anthropic's cache_read_input_tokens/
        cache_creation_input_tokens — clients (e.g. Claude Code) compute
        context-window usage from these fields, and a missing/zeroed field
        looks identical to "no caching happened" to that client. See
        anthropics/claude-code#13385."""
        resp = {
            "output": {"message": {"role": "assistant", "content": [{"text": "hi"}]}},
            "stopReason": "end_turn",
            "usage": {
                "inputTokens": 50,
                "outputTokens": 10,
                "totalTokens": 60,
                "cacheReadInputTokens": 100,
                "cacheWriteInputTokens": 20,
            },
        }
        result = _converse_response_to_anthropic(
            resp, "msg_abc", "qwen.qwen3-coder-next"
        )
        assert result["usage"] == {
            "input_tokens": 50,
            "output_tokens": 10,
            "cache_read_input_tokens": 100,
            "cache_creation_input_tokens": 20,
        }
