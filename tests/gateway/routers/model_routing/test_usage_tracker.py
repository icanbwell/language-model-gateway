"""
Tests for usage_tracker.py.

Tests for usage tracking functionality including data extraction and usage recording.
"""

from __future__ import annotations

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


class TestUsageTrackerInitialization:
    """Tests for UsageTracker initialization."""

    def test_init_with_defaults(self) -> None:
        """Should use default db_name and collection_name when not provided."""
        tracker = UsageTracker(mongo_uri="mongodb://localhost:27017", enabled=True)
        assert tracker._mongo_uri == "mongodb://localhost:27017"
        assert tracker._db_name == "usage_tracker"
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
