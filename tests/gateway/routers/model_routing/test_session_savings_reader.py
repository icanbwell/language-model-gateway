"""
Tests for session_savings_reader.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from language_model_gateway.gateway.routers.model_routing.session_savings_reader import (
    SessionSavingsReader,
)


class TestSessionSavingsReaderInitialization:
    def test_init_with_defaults(self) -> None:
        reader = SessionSavingsReader(mongo_uri="mongodb://localhost:27017")
        assert reader._mongo_uri == "mongodb://localhost:27017"
        assert reader._db_name == "llm_storage"
        assert reader._collection_name == "model-router-sessions"
        assert reader._enabled is True

    def test_init_disabled_does_not_connect(self) -> None:
        reader = SessionSavingsReader(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        assert reader._enabled is False
        assert reader._client is None


class TestSessionSavingsReaderGetSessionSavings:
    async def test_returns_savings_with_all_tiers(self) -> None:
        reader = SessionSavingsReader(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        doc = {
            "session_id": "sess-1",
            "total_savings_usd": 0.42,
            "total_tokens": 12345,
            "low_tier_model": "qwen-coder",
            "low_tier_backend": "aws_bedrock",
            "low_tier_cost": 0.10,
            "low_tier_anthropic_cost": 0.30,
            "medium_tier_model": "claude-sonnet-5",
            "medium_tier_backend": "anthropic",
            "medium_tier_cost": 0.30,
            "medium_tier_anthropic_cost": 0.50,
            "high_tier_model": "claude-opus-4-8",
            "high_tier_cost": 0.02,
            "high_tier_anthropic_cost": 0.06,
        }
        with patch.object(reader, "_ensure_connected", new_callable=AsyncMock):
            reader._collection = MagicMock()
            reader._collection.find_one = AsyncMock(return_value=doc)

            result = await reader.get_session_savings("sess-1")

            assert result is not None
            assert result.session_id == "sess-1"
            assert result.total_savings_usd == 0.42
            assert result.total_tokens == 12345
            assert set(result.tiers.keys()) == {"low", "medium", "high"}
            assert result.tiers["low"].model == "qwen-coder"
            assert result.tiers["low"].backend == "aws_bedrock"
            assert result.tiers["low"].cost_usd == 0.10
            assert result.tiers["low"].anthropic_cost_usd == 0.30
            assert result.tiers["medium"].backend == "anthropic"
            # high tier's backend was never recorded (older rollup, or a
            # pre-fix session) — must be None, not a guessed/default value.
            assert result.tiers["high"].backend is None
            reader._collection.find_one.assert_called_once_with(
                {"session_id": "sess-1"}
            )

    async def test_omits_tiers_the_session_never_used(self) -> None:
        reader = SessionSavingsReader(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        doc = {
            "session_id": "sess-2",
            "total_savings_usd": 0.10,
            "total_tokens": 500,
            "low_tier_model": "qwen-coder",
            "low_tier_cost": 0.05,
            "low_tier_anthropic_cost": 0.15,
        }
        with patch.object(reader, "_ensure_connected", new_callable=AsyncMock):
            reader._collection = MagicMock()
            reader._collection.find_one = AsyncMock(return_value=doc)

            result = await reader.get_session_savings("sess-2")

            assert result is not None
            assert set(result.tiers.keys()) == {"low"}

    async def test_returns_none_when_session_not_found(self) -> None:
        reader = SessionSavingsReader(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        with patch.object(reader, "_ensure_connected", new_callable=AsyncMock):
            reader._collection = MagicMock()
            reader._collection.find_one = AsyncMock(return_value=None)

            result = await reader.get_session_savings("unknown-session")

            assert result is None

    async def test_returns_none_when_disabled(self) -> None:
        reader = SessionSavingsReader(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        with patch.object(reader, "_ensure_connected", new_callable=AsyncMock):
            # _collection stays None since _ensure_connected is mocked and
            # never actually connects.
            result = await reader.get_session_savings("sess-1")
            assert result is None

    async def test_returns_none_on_lookup_failure(self) -> None:
        reader = SessionSavingsReader(
            mongo_uri="mongodb://localhost:27017", enabled=False
        )
        with patch.object(reader, "_ensure_connected", new_callable=AsyncMock):
            reader._collection = MagicMock()
            reader._collection.find_one = AsyncMock(side_effect=RuntimeError("boom"))

            result = await reader.get_session_savings("sess-1")

            assert result is None

    async def test_connection_failure_disables_reader(self) -> None:
        reader = SessionSavingsReader(mongo_uri="mongodb://invalid:27017", enabled=True)
        with patch(
            "pymongo.AsyncMongoClient", side_effect=RuntimeError("connection failed")
        ):
            await reader._ensure_connected()
            assert reader._enabled is False
