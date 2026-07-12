"""
Tests for usage_tracker.py.

Tests for usage tracking functionality including data extraction and usage recording.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from language_model_gateway.gateway.routers.model_routing.usage_tracker import (
    UsageTracker,
)


class TestUsageTrackerDataExtraction:
    """Tests for response data extraction methods."""

    async def test_record_usage_from_anthropic_response(self) -> None:
        """Should extract usage from Anthropic response and record it."""
        auth_info = {
            "user_id": "user-123",
            "email": "user@example.com",
            "user_name": "John Doe",
            "auth_provider": "okta",
            "headers": {
                "x-openwebui-user-id": "user-openwebui-456",
                "x-openwebui-user-email": "openwebui@example.com",
                "x-openwebui-user-name": "OpenWebUI John",
                "x-auth-provider": "auth0",
                "authorization": "Bearer token",
            },
        }

        response_body = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "model": "claude-opus-4-8",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        }

        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        # Mock the _ensure_connected method using patch.object and set _collection directly
        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            # Call record_usage_from_anthropic_response
            await tracker.record_usage_from_anthropic_response(
                request_id="req-123",
                auth_info=auth_info,
                model="claude-opus-4-8",
                response_body=response_body,
            )

            # Verify that insert_one was called with the expected record
            call_args = tracker._collection.insert_one.call_args
            assert call_args is not None

            actual_record = call_args[0][0]
            assert actual_record["request_id"] == "req-123"
            assert actual_record["user_id"] == "user-123"  # From auth_info dict
            assert actual_record["model"] == "claude-opus-4-8"
            assert actual_record["input_tokens"] == 100
            assert actual_record["output_tokens"] == 50
            assert actual_record["auth_provider"] == "okta"  # From auth_info dict
            assert actual_record["email"] == "user@example.com"  # From auth_info dict
            assert actual_record["user_name"] == "John Doe"  # From auth_info dict

    async def test_record_usage_from_openai_response(self) -> None:
        """Should extract usage from OpenAI response and record it."""
        auth_info = {
            "user_id": "user-789",
            "headers": {
                "x-openwebui-user-id": "user-openwebui-999",
            },
        }

        response_body = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 200,
                "completion_tokens": 75,
                "total_tokens": 275,
            },
        }

        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            # Call record_usage_from_openai_response
            await tracker.record_usage_from_openai_response(
                request_id="req-456",
                auth_info=auth_info,
                model="gpt-4",
                response_body=response_body,
            )

            # Verify that insert_one was called with the expected record
            call_args = tracker._collection.insert_one.call_args
            assert call_args is not None

            actual_record = call_args[0][0]
            assert actual_record["request_id"] == "req-456"
            assert actual_record["user_id"] == "user-789"
            assert actual_record["model"] == "gpt-4"
            assert actual_record["input_tokens"] == 200
            assert actual_record["output_tokens"] == 75
            assert actual_record["total_tokens"] == 275

    async def test_record_usage_from_anthropic_response_with_zero_tokens(self) -> None:
        """Should not record usage when both input and output tokens are zero."""
        auth_info = {"user_id": "user-123"}
        response_body = {
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
            },
        }

        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            # Call record_usage_from_anthropic_response
            await tracker.record_usage_from_anthropic_response(
                request_id="req-123",
                auth_info=auth_info,
                model="claude-opus-4-8",
                response_body=response_body,
            )

            # Verify that insert_one was NOT called (since tokens are zero)
            tracker._collection.insert_one.assert_not_called()

    async def test_record_usage_from_openai_response_with_zero_tokens(self) -> None:
        """Should not record usage when both prompt and completion tokens are zero."""
        auth_info = {"user_id": "user-123"}
        response_body = {
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
            },
        }

        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            # Call record_usage_from_openai_response
            await tracker.record_usage_from_openai_response(
                request_id="req-123",
                auth_info=auth_info,
                model="gpt-4",
                response_body=response_body,
            )

            # Verify that insert_one was NOT called (since tokens are zero)
            tracker._collection.insert_one.assert_not_called()

    async def test_record_usage_missing_usage_field(self) -> None:
        """Should handle missing usage field in response gracefully."""
        auth_info = {"user_id": "user-123"}
        response_body = {
            "id": "msg_123",
            "type": "message",
        }

        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            # Call record_usage_from_anthropic_response without usage field
            await tracker.record_usage_from_anthropic_response(
                request_id="req-123",
                auth_info=auth_info,
                model="claude-opus-4-8",
                response_body=response_body,
            )

            # Verify that insert_one was NOT called (since tokens default to 0)
            tracker._collection.insert_one.assert_not_called()


class TestUsageTrackerSessionIdAndTimestamp:
    """Tests for session_id and timestamp fields on recorded usage."""

    async def test_record_usage_includes_timestamp(self) -> None:
        """Every recorded usage document should carry a UTC timestamp."""
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert isinstance(actual_record["timestamp"], datetime)

    async def test_record_usage_includes_session_id_when_present(self) -> None:
        """session_id should be recorded when supplied via auth_info."""
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
                session_id="sess-1",
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["session_id"] == "sess-1"

    async def test_record_usage_omits_session_id_when_absent(self) -> None:
        """session_id should not appear in the record when not supplied."""
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert "session_id" not in actual_record

    async def test_record_usage_from_openai_response_threads_session_id(self) -> None:
        """auth_info's session_id should flow through to the recorded document."""
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage_from_openai_response(
                request_id="req-1",
                auth_info={"user_id": "user-1", "session_id": "sess-1"},
                model="gpt-4",
                response_body={
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                },
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["session_id"] == "sess-1"

    async def test_record_usage_includes_account_uuid_when_present(self) -> None:
        """account_uuid should be recorded even when it doesn't resolve to a user_id.

        Email resolution now happens downstream in reporting, not in this
        hot path, so account_uuid must survive on the record on its own.
        """
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id=None,
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
                account_uuid="acct-123",
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["account_uuid"] == "acct-123"
            assert "user_id" not in actual_record

    async def test_record_usage_omits_account_uuid_when_absent(self) -> None:
        """account_uuid should not appear in the record when not supplied."""
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert "account_uuid" not in actual_record

    async def test_record_usage_from_openai_response_threads_account_uuid(self) -> None:
        """auth_info's account_uuid should flow through to the recorded document."""
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage_from_openai_response(
                request_id="req-1",
                auth_info={"account_uuid": "acct-123"},
                model="gpt-4",
                response_body={
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                },
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["account_uuid"] == "acct-123"

    async def test_record_usage_includes_model_tier_when_present(self) -> None:
        """model_tier should be recorded when supplied by the caller."""
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
                model_tier="premium",
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["model_tier"] == "premium"

    async def test_record_usage_omits_model_tier_when_absent(self) -> None:
        """model_tier should not appear in the record when not supplied."""
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert "model_tier" not in actual_record

    async def test_record_usage_from_openai_response_threads_model_tier(self) -> None:
        """model_tier passed into record_usage_from_openai_response should be recorded."""
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage_from_openai_response(
                request_id="req-1",
                auth_info={"user_id": "user-1"},
                model="gpt-4",
                response_body={
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                },
                model_tier="premium",
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["model_tier"] == "premium"


class TestUsageTrackerBackendAndCost:
    """Tests for backend and cost/savings fields on recorded usage."""

    async def test_record_usage_includes_backend_when_present(self) -> None:
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
                backend="aws_bedrock",
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["backend"] == "aws_bedrock"

    async def test_record_usage_computes_cost_and_savings(self) -> None:
        """cost_usd is actual price; cost_savings_usd is vs the Anthropic baseline."""
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="qwen.qwen3-coder-next",
                input_tokens=1_000_000,
                output_tokens=0,
                price_per_mtok=0.5,
                anthropic_price_per_mtok=3.0,
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["cost_usd"] == 0.5
            assert actual_record["cost_savings_usd"] == 2.5

    async def test_record_usage_omits_savings_without_baseline_price(self) -> None:
        """cost_usd is recorded even with no baseline to compare against."""
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=1_000_000,
                output_tokens=0,
                price_per_mtok=5.0,
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["cost_usd"] == 5.0
            assert "cost_savings_usd" not in actual_record

    async def test_record_usage_from_openai_response_threads_backend_and_cost(
        self,
    ) -> None:
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage_from_openai_response(
                request_id="req-1",
                auth_info={"user_id": "user-1"},
                model="gpt-4",
                response_body={
                    "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 0},
                },
                backend="aws_bedrock",
                price_per_mtok=0.15,
                anthropic_price_per_mtok=1.0,
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["backend"] == "aws_bedrock"
            assert actual_record["cost_usd"] == 0.15
            assert actual_record["cost_savings_usd"] == 0.85


class TestUsageTrackerStreamingAndCompression:
    """Tests for streaming/compression metadata fields."""

    async def test_record_usage_includes_streaming_true(self) -> None:
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
                streaming=True,
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["streaming"] is True

    async def test_record_usage_includes_streaming_false(self) -> None:
        """streaming=False should still be recorded — falsy is not the same as absent."""
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
                streaming=False,
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["streaming"] is False

    async def test_record_usage_omits_streaming_when_not_supplied(self) -> None:
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert "streaming" not in actual_record

    async def test_record_usage_includes_compression_fields(self) -> None:
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
                compression_requested="gzip, deflate, br, zstd",
                compression_used="gzip",
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["compression_requested"] == "gzip, deflate, br, zstd"
            assert actual_record["compression_used"] == "gzip"


class TestUsageTrackerCustomHeaders:
    """Tests for the open-ended custom_headers passthrough field."""

    async def test_record_usage_includes_custom_headers_dict(self) -> None:
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
                custom_headers={"user-id": "imran.qureshi@bwell.com", "project": "lmg"},
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["custom_headers"] == {
                "user-id": "imran.qureshi@bwell.com",
                "project": "lmg",
            }

    async def test_record_usage_omits_custom_headers_when_absent(self) -> None:
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert "custom_headers" not in actual_record

    async def test_record_usage_from_openai_response_threads_custom_headers(
        self,
    ) -> None:
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage_from_openai_response(
                request_id="req-1",
                auth_info={"custom_headers": {"project": "lmg"}},
                model="gpt-4",
                response_body={
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                },
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["custom_headers"] == {"project": "lmg"}


class TestUsageTrackerPreviews:
    """Tests for opt-in prompt/response preview capture."""

    async def test_preview_omitted_by_default(self) -> None:
        """Previews should not be written when capture_previews is left at its default (off)."""
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
                prompt_text="what does this function do?",
                response_text="it parses the request body.",
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert "input_preview" not in actual_record
            assert "output_preview" not in actual_record

    async def test_preview_recorded_when_capture_enabled(self) -> None:
        """Previews should be written when capture_previews is explicitly enabled."""
        tracker = UsageTracker(
            mongo_uri="mongodb://localhost:27017",
            enabled=False,
            capture_previews=True,
        )

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
                prompt_text="what does this function do?",
                response_text="it parses the request body.",
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["input_preview"] == "what does this function do?"
            assert actual_record["output_preview"] == "it parses the request body."

    async def test_preview_truncated_to_configured_length(self) -> None:
        """Preview text should be truncated to preview_chars."""
        tracker = UsageTracker(
            mongo_uri="mongodb://localhost:27017",
            enabled=False,
            capture_previews=True,
            preview_chars=5,
        )

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
                prompt_text="0123456789",
                response_text="abcdefghij",
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["input_preview"] == "01234…"
            assert actual_record["output_preview"] == "abcde…"

    async def test_preview_not_marked_truncated_when_within_limit(self) -> None:
        """Text at or under preview_chars should be stored as-is, with no marker."""
        tracker = UsageTracker(
            mongo_uri="mongodb://localhost:27017",
            enabled=False,
            capture_previews=True,
            preview_chars=10,
        )

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage(
                request_id="req-1",
                user_id="user-1",
                model="claude-opus-4-8",
                input_tokens=10,
                output_tokens=5,
                prompt_text="0123456789",
                response_text="abcde",
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["input_preview"] == "0123456789"
            assert actual_record["output_preview"] == "abcde"

    async def test_record_usage_from_anthropic_response_extracts_output_preview(
        self,
    ) -> None:
        """Output preview should be extracted from Anthropic content text blocks."""
        tracker = UsageTracker(
            mongo_uri="mongodb://localhost:27017",
            enabled=False,
            capture_previews=True,
        )

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage_from_anthropic_response(
                request_id="req-1",
                auth_info={"user_id": "user-1"},
                model="claude-opus-4-8",
                response_body={
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                    "content": [{"type": "text", "text": "here is the answer"}],
                },
                prompt_text="what is the answer?",
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["input_preview"] == "what is the answer?"
            assert actual_record["output_preview"] == "here is the answer"

    async def test_record_usage_from_openai_response_extracts_output_preview(
        self,
    ) -> None:
        """Output preview should be extracted from the OpenAI message content."""
        tracker = UsageTracker(
            mongo_uri="mongodb://localhost:27017",
            enabled=False,
            capture_previews=True,
        )

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_usage_from_openai_response(
                request_id="req-1",
                auth_info={"user_id": "user-1"},
                model="gpt-4",
                response_body={
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                    "choices": [{"message": {"content": "here is the answer"}}],
                },
                prompt_text="what is the answer?",
            )

            actual_record = tracker._collection.insert_one.call_args[0][0]
            assert actual_record["input_preview"] == "what is the answer?"
            assert actual_record["output_preview"] == "here is the answer"


class TestUsageTrackerInitialization:
    """Tests for UsageTracker initialization."""

    def test_init_with_defaults(self) -> None:
        """Should use default db_name and collection_name when not provided."""
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=True)
        assert tracker._mongo_uri == "mongodb://localhost:27017"
        assert tracker._db_name == "llm_storage"
        assert tracker._collection_name == "usage"
        assert tracker._enabled is True

    def test_init_with_custom_values(self) -> None:
        """Should use custom values when provided."""
        tracker = UsageTracker(
            mongo_uri="mongodb://localhost:27017",
            db_name="custom_db",
            collection_name="custom_collection",
            enabled=True,
        )
        assert tracker._mongo_uri == "mongodb://localhost:27017"
        assert tracker._db_name == "custom_db"
        assert tracker._collection_name == "custom_collection"
        assert tracker._enabled is True

    def test_init_disabled_does_not_connect(self) -> None:
        """Should not connect when enabled is False."""
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=False)
        assert tracker._enabled is False
        assert tracker._client is None
