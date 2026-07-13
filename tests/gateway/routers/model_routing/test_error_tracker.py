"""
Tests for error_tracker.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from language_model_gateway.gateway.routers.model_routing.error_tracker import (
    ErrorTracker,
)

_TEST_START_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


class TestErrorTrackerInitialization:
    """Tests for ErrorTracker initialization."""

    def test_init_with_defaults(self) -> None:
        tracker = ErrorTracker(mongo_uri="mongodb://localhost:27017", enabled=True)
        assert tracker._mongo_uri == "mongodb://localhost:27017"
        assert tracker._db_name == "llm_storage"
        assert tracker._collection_name == "errors"
        assert tracker._enabled is True

    def test_init_with_custom_values(self) -> None:
        tracker = ErrorTracker(
            mongo_uri="mongodb://localhost:27017",
            db_name="custom_db",
            collection_name="custom_errors",
            enabled=True,
        )
        assert tracker._db_name == "custom_db"
        assert tracker._collection_name == "custom_errors"

    def test_init_disabled_does_not_connect(self) -> None:
        tracker = ErrorTracker(mongo_uri="mongodb://localhost:27017", enabled=False)
        assert tracker._enabled is False
        assert tracker._client is None


class TestErrorTrackerRecordError:
    """Tests for record_error."""

    async def test_records_expected_fields(self) -> None:
        tracker = ErrorTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_error(
                request_id="req-1",
                model="claude-opus-4-8",
                error_type="upstream_error",
                error_message="upstream returned 503",
                start_time=_TEST_START_TIME,
                user_id="user-1",
                session_id="sess-1",
                account_uuid="acct-1",
                agent_id="agent-1",
                parent_agent_id="parent-1",
                model_tier="opus",
                backend="anthropic",
                auth="passthrough",
                api_type="anthropic",
                streaming=True,
                status_code=503,
                response_headers={"x-amzn-requestid": "req-abc-123"},
            )

            record = tracker._collection.insert_one.call_args[0][0]
            assert record["request_id"] == "req-1"
            assert record["model"] == "claude-opus-4-8"
            assert record["error_type"] == "upstream_error"
            assert record["error_message"] == "upstream returned 503"
            assert record["start_time"] == _TEST_START_TIME
            assert isinstance(record["end_time"], datetime)
            assert isinstance(record["duration_ms"], float)
            assert record["user_id"] == "user-1"
            assert record["session_id"] == "sess-1"
            assert record["account_uuid"] == "acct-1"
            assert record["agent_id"] == "agent-1"
            assert record["parent_agent_id"] == "parent-1"
            assert record["model_tier"] == "opus"
            assert record["backend"] == "anthropic"
            assert record["auth"] == "passthrough"
            assert record["api_type"] == "anthropic"
            assert record["streaming"] is True
            assert record["status_code"] == 503
            assert record["response_headers"] == {"x-amzn-requestid": "req-abc-123"}

    async def test_omits_optional_fields_when_absent(self) -> None:
        tracker = ErrorTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_error(
                request_id="req-1",
                model="claude-opus-4-8",
                error_type="upstream_error",
                error_message="boom",
                start_time=_TEST_START_TIME,
            )

            record = tracker._collection.insert_one.call_args[0][0]
            for field in (
                "user_id",
                "session_id",
                "account_uuid",
                "agent_id",
                "parent_agent_id",
                "model_tier",
                "backend",
                "auth",
                "api_type",
                "streaming",
                "status_code",
                "response_headers",
            ):
                assert field not in record

    async def test_truncates_long_error_message(self) -> None:
        tracker = ErrorTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock()

            await tracker.record_error(
                request_id="req-1",
                model="claude-opus-4-8",
                error_type="upstream_error",
                error_message="x" * 2000,
                start_time=_TEST_START_TIME,
            )

            record = tracker._collection.insert_one.call_args[0][0]
            assert len(record["error_message"]) == 1000

    async def test_noop_when_collection_unavailable(self) -> None:
        tracker = ErrorTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            await tracker.record_error(
                request_id="req-1",
                model="claude-opus-4-8",
                error_type="upstream_error",
                error_message="boom",
                start_time=_TEST_START_TIME,
            )
            # No exception raised; nothing to assert on since _collection is None.

    async def test_write_failure_does_not_raise(self) -> None:
        tracker = ErrorTracker(mongo_uri="mongodb://localhost:27017", enabled=False)

        with patch.object(tracker, "_ensure_connected", new_callable=AsyncMock):
            tracker._collection = MagicMock()
            tracker._collection.insert_one = AsyncMock(side_effect=RuntimeError("boom"))

            await tracker.record_error(
                request_id="req-1",
                model="claude-opus-4-8",
                error_type="upstream_error",
                error_message="boom",
                start_time=_TEST_START_TIME,
            )
