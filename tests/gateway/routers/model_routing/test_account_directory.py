"""
Tests for account_directory.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from language_model_gateway.gateway.routers.model_routing.account_directory import (
    AccountDirectory,
    extract_account_uuid,
    extract_session_id,
)


class TestExtractAccountUuid:
    """Tests for extracting account_uuid from Claude Code's request metadata."""

    def test_extracts_account_uuid_from_valid_metadata(self) -> None:
        body_json = {
            "metadata": {
                "user_id": (
                    '{"device_id": "dev-1", "account_uuid": "acct-123", '
                    '"session_id": "sess-1"}'
                )
            }
        }
        assert extract_account_uuid(body_json) == "acct-123"

    def test_returns_none_when_metadata_missing(self) -> None:
        assert extract_account_uuid({}) is None

    def test_returns_none_when_metadata_not_dict(self) -> None:
        assert extract_account_uuid({"metadata": "not-a-dict"}) is None

    def test_returns_none_when_user_id_not_string(self) -> None:
        assert extract_account_uuid({"metadata": {"user_id": 123}}) is None

    def test_returns_none_when_user_id_not_valid_json(self) -> None:
        assert extract_account_uuid({"metadata": {"user_id": "not json"}}) is None

    def test_returns_none_when_parsed_json_not_dict(self) -> None:
        assert extract_account_uuid({"metadata": {"user_id": "[1, 2, 3]"}}) is None

    def test_returns_none_when_account_uuid_missing(self) -> None:
        body_json = {"metadata": {"user_id": '{"device_id": "dev-1"}'}}
        assert extract_account_uuid(body_json) is None

    def test_returns_none_when_account_uuid_not_string(self) -> None:
        body_json = {"metadata": {"user_id": '{"account_uuid": 123}'}}
        assert extract_account_uuid(body_json) is None


class TestExtractSessionId:
    """Tests for extracting session_id from Claude Code's request metadata."""

    def test_extracts_session_id_from_valid_metadata(self) -> None:
        body_json = {
            "metadata": {
                "user_id": (
                    '{"device_id": "dev-1", "account_uuid": "acct-123", '
                    '"session_id": "sess-1"}'
                )
            }
        }
        assert extract_session_id(body_json) == "sess-1"

    def test_returns_none_when_metadata_missing(self) -> None:
        assert extract_session_id({}) is None

    def test_returns_none_when_session_id_missing(self) -> None:
        body_json = {"metadata": {"user_id": '{"account_uuid": "acct-123"}'}}
        assert extract_session_id(body_json) is None

    def test_returns_none_when_session_id_not_string(self) -> None:
        body_json = {"metadata": {"user_id": '{"session_id": 123}'}}
        assert extract_session_id(body_json) is None


class TestAccountDirectoryInitialization:
    """Tests for AccountDirectory initialization."""

    def test_init_with_defaults(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://localhost:27017", enabled=True
        )
        assert directory._mongo_uri == "mongodb://localhost:27017"
        assert directory._db_name == "llm_storage"
        assert directory._collection_name == "account_directory"
        assert directory._enabled is True

    def test_init_with_custom_values(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://localhost:27017",
            db_name="custom_db",
            collection_name="custom_collection",
            enabled=True,
        )
        assert directory._db_name == "custom_db"
        assert directory._collection_name == "custom_collection"

    def test_init_disabled_does_not_connect(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        assert directory._enabled is False
        assert directory._client is None


class TestAccountDirectoryResolveEmail:
    """Tests for AccountDirectory.resolve_email."""

    async def test_resolve_email_found(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        with patch.object(directory, "_ensure_connected", new_callable=AsyncMock):
            directory._collection = MagicMock()
            directory._collection.find_one = AsyncMock(
                return_value={"_id": "acct-123", "email": "person@example.com"}
            )
            result = await directory.resolve_email("acct-123")
            assert result == "person@example.com"
            directory._collection.find_one.assert_called_once_with({"_id": "acct-123"})

    async def test_resolve_email_not_found(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        with patch.object(directory, "_ensure_connected", new_callable=AsyncMock):
            directory._collection = MagicMock()
            directory._collection.find_one = AsyncMock(return_value=None)
            result = await directory.resolve_email("unknown-acct")
            assert result is None

    async def test_resolve_email_when_disabled_returns_none(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        with patch.object(directory, "_ensure_connected", new_callable=AsyncMock):
            # _collection stays None since _ensure_connected is mocked and never
            # actually connects.
            result = await directory.resolve_email("acct-123")
            assert result is None

    async def test_resolve_email_lookup_failure_returns_none(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        with patch.object(directory, "_ensure_connected", new_callable=AsyncMock):
            directory._collection = MagicMock()
            directory._collection.find_one = AsyncMock(side_effect=RuntimeError("boom"))
            result = await directory.resolve_email("acct-123")
            assert result is None

    async def test_connection_failure_disables_directory(self) -> None:
        directory = AccountDirectory(mongo_uri="mongodb://invalid:27017", enabled=True)
        with patch(
            "pymongo.AsyncMongoClient", side_effect=RuntimeError("connection failed")
        ):
            await directory._ensure_connected()
            assert directory._enabled is False

    async def test_resolve_email_second_call_uses_cache(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        with patch.object(
            directory, "_ensure_connected", new_callable=AsyncMock
        ) as mock_ensure_connected:
            directory._collection = MagicMock()
            directory._collection.find_one = AsyncMock(
                return_value={"_id": "acct-123", "email": "person@example.com"}
            )

            first_result = await directory.resolve_email("acct-123")
            second_result = await directory.resolve_email("acct-123")

            assert first_result == "person@example.com"
            assert second_result == "person@example.com"
            directory._collection.find_one.assert_called_once_with({"_id": "acct-123"})
            mock_ensure_connected.assert_called_once()

    async def test_resolve_email_not_found_is_cached(self) -> None:
        directory = AccountDirectory(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        with patch.object(
            directory, "_ensure_connected", new_callable=AsyncMock
        ) as mock_ensure_connected:
            directory._collection = MagicMock()
            directory._collection.find_one = AsyncMock(return_value=None)

            first_result = await directory.resolve_email("unknown-acct")
            second_result = await directory.resolve_email("unknown-acct")

            assert first_result is None
            assert second_result is None
            directory._collection.find_one.assert_called_once_with(
                {"_id": "unknown-acct"}
            )
            mock_ensure_connected.assert_called_once()
