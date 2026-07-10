"""
Tests for usage_tracker.py and usage_manager.py.

Tests for usage tracking functionality including header extraction and usage recording.
"""

from __future__ import annotations

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from language_model_gateway.gateway.routers.model_routing.usage_tracker import (
    UsageTracker,
)
from language_model_gateway.gateway.managers.usage_manager import UsageManager


# Mock AuthInformation class for testing
class MockAuthInformation:
    """Mock auth information object for testing."""

    def __init__(
        self,
        subject: str | None = None,
        email: str | None = None,
        user_name: str | None = None,
        auth_provider: str | None = None,
    ) -> None:
        self.subject = subject
        self.email = email
        self.user_name = user_name
        self.auth_provider = auth_provider


class TestUsageTrackerHeaderExtraction:
    """Tests for header extraction methods."""

    def test_extract_user_id_from_headers_x_openwebui_preferred(self) -> None:
        """Should prefer x-openwebui-user-id over legacy x-customer-id."""
        headers = {
            "x-openwebui-user-id": "user-openwebui-123",
            "x-customer-id": "user-legacy-456",
        }
        result = UsageTracker.extract_user_id_from_headers(headers)
        assert result == "user-openwebui-123"

    def test_extract_user_id_from_headers_fallback_to_legacy(self) -> None:
        """Should fall back to x-customer-id when x-openwebui header is absent."""
        headers = {
            "x-customer-id": "user-legacy-456",
        }
        result = UsageTracker.extract_user_id_from_headers(headers)
        assert result == "user-legacy-456"

    def test_extract_user_id_from_headers_returns_none_when_missing(self) -> None:
        """Should return None when neither header is present."""
        headers = {"other-header": "value"}
        result = UsageTracker.extract_user_id_from_headers(headers)
        assert result is None

    def test_extract_user_id_from_headers_empty_headers(self) -> None:
        """Should return None for empty or None headers."""
        result = UsageTracker.extract_user_id_from_headers(None)
        assert result is None

        result = UsageTracker.extract_user_id_from_headers({})
        assert result is None

    def test_extract_email_from_headers_x_openwebui_preferred(self) -> None:
        """Should prefer x-openwebui-user-email over legacy x-email."""
        headers = {
            "x-openwebui-user-email": "user@example.com",
            "x-email": "legacy@example.com",
        }
        result = UsageTracker.extract_email_from_headers(headers)
        assert result == "user@example.com"

    def test_extract_email_from_headers_fallback_to_legacy(self) -> None:
        """Should fall back to x-email when x-openwebui header is absent."""
        headers = {
            "x-email": "legacy@example.com",
        }
        result = UsageTracker.extract_email_from_headers(headers)
        assert result == "legacy@example.com"

    def test_extract_email_from_headers_returns_none_when_missing(self) -> None:
        """Should return None when neither header is present."""
        headers = {"other-header": "value"}
        result = UsageTracker.extract_email_from_headers(headers)
        assert result is None

    def test_extract_user_name_from_headers_x_openwebui_preferred(self) -> None:
        """Should prefer x-openwebui-user-name over legacy x-user-name."""
        headers = {
            "x-openwebui-user-name": "John Doe",
            "x-user-name": "Legacy John",
        }
        result = UsageTracker.extract_user_name_from_headers(headers)
        assert result == "John Doe"

    def test_extract_user_name_from_headers_fallback_to_legacy(self) -> None:
        """Should fall back to x-user-name when x-openwebui header is absent."""
        headers = {
            "x-user-name": "Legacy John",
        }
        result = UsageTracker.extract_user_name_from_headers(headers)
        assert result == "Legacy John"

    def test_extract_user_name_from_headers_returns_none_when_missing(self) -> None:
        """Should return None when neither header is present."""
        headers = {"other-header": "value"}
        result = UsageTracker.extract_user_name_from_headers(headers)
        assert result is None


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


class TestUsageManagerHeaderExtraction:
    """Tests for UsageManager header extraction methods."""

    def test_extract_user_id_from_auth_subject(self) -> None:
        """Should extract user_id from auth_information subject."""
        auth_info = MockAuthInformation(subject="user-123")
        result = UsageManager.extract_user_id(auth_information=auth_info)
        assert result == "user-123"

    def test_extract_user_id_from_auth_email(self) -> None:
        """Should fall back to email when subject is not available."""
        auth_info = MockAuthInformation(email="user@example.com")
        result = UsageManager.extract_user_id(auth_information=auth_info)
        assert result == "user@example.com"

    def test_extract_user_id_from_headers_x_openwebui(self) -> None:
        """Should extract user_id from x-openwebui-user-id header."""
        headers = {"x-openwebui-user-id": "user-123"}
        result = UsageManager.extract_user_id(auth_information=None, headers=headers)
        assert result == "user-123"

    def test_extract_user_id_default_anonymous(self) -> None:
        """Should return 'anonymous' when no user info is available."""
        result = UsageManager.extract_user_id(
            auth_information=None, headers={"other": "value"}
        )
        assert result == "anonymous"

    def test_extract_user_id_empty_auth_info(self) -> None:
        """Should return 'anonymous' with empty auth info and headers."""
        result = UsageManager.extract_user_id(auth_information=None, headers={})
        assert result == "anonymous"

    def test_extract_email_from_auth(self) -> None:
        """Should extract email from auth_information."""
        auth_info = MockAuthInformation(email="user@example.com")
        result = UsageManager.extract_email(auth_information=auth_info)
        assert result == "user@example.com"

    def test_extract_email_from_headers(self) -> None:
        """Should extract email from x-openwebui-user-email header."""
        headers = {"x-openwebui-user-email": "user@example.com"}
        result = UsageManager.extract_email(auth_information=None, headers=headers)
        assert result == "user@example.com"

    def test_extract_email_none_when_missing(self) -> None:
        """Should return None when email is not available."""
        result = UsageManager.extract_email(
            auth_information=None, headers={"other": "value"}
        )
        assert result is None

    def test_extract_user_name_from_auth(self) -> None:
        """Should extract user_name from auth_information."""
        auth_info = MockAuthInformation(user_name="John Doe")
        result = UsageManager.extract_user_name(auth_information=auth_info)
        assert result == "John Doe"

    def test_extract_user_name_from_headers(self) -> None:
        """Should extract user_name from x-openwebui-user-name header."""
        headers = {"x-openwebui-user-name": "John Doe"}
        result = UsageManager.extract_user_name(auth_information=None, headers=headers)
        assert result == "John Doe"

    def test_extract_user_name_none_when_missing(self) -> None:
        """Should return None when user_name is not available."""
        result = UsageManager.extract_user_name(
            auth_information=None, headers={"other": "value"}
        )
        assert result is None

    def test_extract_auth_provider_from_auth(self) -> None:
        """Should extract auth_provider from auth_information."""
        auth_info = MockAuthInformation(auth_provider="okta")
        result = UsageManager.extract_auth_provider(auth_information=auth_info)
        assert result == "okta"

    def test_extract_auth_provider_none_when_missing(self) -> None:
        """Should return None when auth_provider is not available."""
        result = UsageManager.extract_auth_provider(auth_information=None)
        assert result is None


class TestUsageManagerRequestRecording:
    """Tests for UsageManager record usage from request."""

    async def test_record_usage_from_request(self) -> None:
        """Should extract info from request and record usage."""
        auth_info = MockAuthInformation(
            subject="user-123",
            email="user@example.com",
            user_name="John Doe",
            auth_provider="okta",
        )
        headers = {"x-openwebui-user-name": "OpenWebUI John"}

        mock_collection = MagicMock()
        mock_collection.insert_one = AsyncMock()

        with patch(
            "language_model_gateway.gateway.managers.usage_manager.AsyncMongoClient"
        ) as mock_client:
            mock_client.return_value.__getitem__ = MagicMock(
                return_value=mock_collection
            )
            mock_client.return_value.__getitem__.__getitem__ = MagicMock(
                return_value=mock_collection
            )

            manager = UsageManager(
                mongo_client=mock_client.return_value,
                db_name="test_db",
                collection_name="usage",
            )

            # Override _collection for direct testing
            manager._collection = mock_collection

            await manager.record_usage_from_request(
                request_id="req-123",
                model="claude-opus-4-8",
                input_tokens=100,
                output_tokens=50,
                auth_information=auth_info,
                headers=headers,
                timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            )

            # Verify record was created with correct values
            call_args = mock_collection.insert_one.call_args
            assert call_args is not None

            actual_record = call_args[0][0]
            assert actual_record["request_id"] == "req-123"
            assert actual_record["user_id"] == "user-123"
            assert actual_record["email"] == "user@example.com"
            assert actual_record["user_name"] == "John Doe"  # From auth, not headers
            assert actual_record["auth_provider"] == "okta"
            assert actual_record["model"] == "claude-opus-4-8"
            assert actual_record["input_tokens"] == 100
            assert actual_record["output_tokens"] == 50
