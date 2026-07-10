"""
Usage tracking manager for recording model API calls by user.

This manager tracks usage data including:
- Request ID
- User ID (extracted from auth information or headers)
- Model name
- Input/output token counts
- Timestamp of request
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, UTC
from typing import Any, Dict, Optional, List
from typing_extensions import TypedDict

# Use pymongo built-in async client (available since pymongo 4.4)
from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import PyMongoError

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("USAGE", logging.INFO))


class UsageData(TypedDict):
    """TypedDict for usage data structure."""

    request_id: str
    user_id: str
    model: str
    input_tokens: int
    output_tokens: int
    timestamp: datetime
    auth_provider: Optional[str]
    email: Optional[str]
    user_name: Optional[str]


class UsageManager:
    """
    Manages usage tracking for language model API calls.

    Stores usage data in MongoDB with the following schema:
    - _id: ObjectId
    - request_id: str (unique request identifier)
    - user_id: str (subject, email, or x-openwebui-user-id header)
    - model: str (name of the model used)
    - input_tokens: int (number of input tokens)
    - output_tokens: int (number of output tokens)
    - timestamp: datetime (ISO 8601 timestamp)
    - email: Optional[str] (user email if available)
    - user_name: Optional[str] (user name if available)
    - auth_provider: Optional[str] (OAuth provider if used)
    """

    def __init__(
        self,
        *,
        mongo_client: AsyncMongoClient[Any],
        db_name: str,
        collection_name: str = "usage",
    ) -> None:
        """
        Initialize the UsageManager.

        Args:
            mongo_client: AsyncMongoClient instance
            db_name: Name of the MongoDB database
            collection_name: Name of the collection to store usage data
        """
        self._mongo_client: AsyncMongoClient[Any] = mongo_client
        self._db_name: str = db_name
        self._collection_name: str = collection_name
        self._collection: AsyncCollection[Any] = mongo_client[db_name][collection_name]

        # Create index on user_id for efficient queries
        # Note: This is an async method but called from sync __init__, so we fire it and forget
        asyncio.create_task(self._create_indexes())  # type: ignore[unused-awaitable]

    async def _create_indexes(self) -> None:
        """Create indexes for efficient querying."""
        try:
            # Index on user_id
            await self._collection.create_index("user_id")
            # Index on timestamp for time-based queries
            await self._collection.create_index("timestamp")
            # Index on model for model-specific queries
            await self._collection.create_index("model")
            # Compound index for common query patterns
            await self._collection.create_index([("user_id", 1), ("timestamp", -1)])
            logger.info(
                f"Created indexes for usage collection: {self._collection_name}"
            )
        except PyMongoError as e:
            logger.error(f"Failed to create indexes for usage collection: {e}")

    @staticmethod
    def extract_user_id(
        auth_information: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Extract user ID from auth information or headers.

        Priority order:
        1. auth_information.subject
        2. auth_information.email
        3. x-openwebui-user-id header
        4. "anonymous" if no user info found

        Args:
            auth_information: AuthInformation object with subject/email
            headers: Request headers including x-openwebui-user-id

        Returns:
            A string user ID
        """
        if auth_information and hasattr(auth_information, "subject"):
            subject = getattr(auth_information, "subject", None)
            if subject:
                return str(subject)

        if auth_information and hasattr(auth_information, "email"):
            email = getattr(auth_information, "email", None)
            if email:
                return str(email)

        if headers:
            user_id_header = headers.get("x-openwebui-user-id")
            if user_id_header:
                return str(user_id_header)

        return "anonymous"

    @staticmethod
    def extract_user_name(
        auth_information: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """Extract user name from auth information or headers."""
        if auth_information and hasattr(auth_information, "user_name"):
            return getattr(auth_information, "user_name", None)
        if headers:
            return headers.get("x-openwebui-user-name")
        return None

    @staticmethod
    def extract_email(
        auth_information: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """Extract email from auth information or headers."""
        if auth_information and hasattr(auth_information, "email"):
            return getattr(auth_information, "email", None)
        if headers:
            return headers.get("x-openwebui-user-email")
        return None

    @staticmethod
    def extract_auth_provider(
        auth_information: Optional[Any] = None,
    ) -> Optional[str]:
        """Extract auth provider from auth information."""
        if auth_information and hasattr(auth_information, "auth_provider"):
            return getattr(auth_information, "auth_provider", None)
        return None

    async def record_usage(
        self,
        *,
        request_id: str,
        user_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        auth_provider: Optional[str] = None,
        email: Optional[str] = None,
        user_name: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Record usage data for a single request.

        Args:
            request_id: Unique request identifier
            user_id: User ID (extracted from auth info)
            model: Model name used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            auth_provider: OAuth provider name if applicable
            email: User email if available
            user_name: User name if available
            timestamp: Request timestamp (defaults to now)

        Returns:
            True if successful, False otherwise
        """
        try:
            usage_data: UsageData = {
                "request_id": request_id,
                "user_id": user_id,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "timestamp": timestamp or datetime.now(UTC),
                "auth_provider": auth_provider,
                "email": email,
                "user_name": user_name,
            }

            await self._collection.insert_one(usage_data)
            logger.info(
                f"Recorded usage: {input_tokens} input, {output_tokens} output tokens "
                f"for model {model}, user {user_id}"
            )
            return True
        except PyMongoError as e:
            logger.error(f"Failed to record usage: {e}")
            return False

    async def record_usage_from_request(
        self,
        *,
        request_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        auth_information: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Record usage data from request context.

        Args:
            request_id: Unique request identifier
            model: Model name used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            auth_information: AuthInformation object with user details
            headers: Request headers
            timestamp: Request timestamp (defaults to now)

        Returns:
            True if successful, False otherwise
        """
        user_id = self.extract_user_id(
            auth_information=auth_information, headers=headers
        )
        email = self.extract_email(auth_information=auth_information, headers=headers)
        user_name = self.extract_user_name(
            auth_information=auth_information, headers=headers
        )
        auth_provider = self.extract_auth_provider(auth_information=auth_information)

        return await self.record_usage(
            request_id=request_id,
            user_id=user_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            auth_provider=auth_provider,
            email=email,
            user_name=user_name,
            timestamp=timestamp,
        )

    async def get_user_usage(
        self,
        *,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        model: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get usage records for a specific user.

        Args:
            user_id: User ID to query
            start_time: Optional start time filter
            end_time: Optional end time filter
            model: Optional model name filter
            limit: Maximum number of records to return

        Returns:
            List of usage records
        """
        query: Dict[str, Any] = {"user_id": user_id}

        if start_time or end_time:
            query["timestamp"] = {}
            if start_time:
                query["timestamp"]["$gte"] = start_time
            if end_time:
                query["timestamp"]["$lte"] = end_time

        if model:
            query["model"] = model

        try:
            cursor = self._collection.find(query).sort("timestamp", -1).limit(limit)
            return [doc async for doc in cursor]
        except PyMongoError as e:
            logger.error(f"Failed to get user usage: {e}")
            return []

    async def get_usage_summary(
        self,
        *,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated usage summary.

        Args:
            user_id: Optional user ID to filter by
            start_time: Optional start time filter
            end_time: Optional end time filter
            model: Optional model name filter

        Returns:
            Dictionary with total_requests, total_input_tokens, total_output_tokens
        """
        query: Dict[str, Any] = {}
        if user_id:
            query["user_id"] = user_id
        if start_time or end_time:
            query["timestamp"] = {}
            if start_time:
                query["timestamp"]["$gte"] = start_time
            if end_time:
                query["timestamp"]["$lte"] = end_time
        if model:
            query["model"] = model

        try:
            pipeline: List[Dict[str, Any]] = [
                {"$match": query},
                {
                    "$group": {
                        "_id": None,
                        "total_requests": {"$sum": 1},
                        "total_input_tokens": {"$sum": "$input_tokens"},
                        "total_output_tokens": {"$sum": "$output_tokens"},
                    }
                },
            ]

            cursor = await self._collection.aggregate(pipeline)
            result = await cursor.to_list(length=1)

            if result:
                return {
                    "total_requests": result[0]["total_requests"],
                    "total_input_tokens": result[0].get("total_input_tokens", 0),
                    "total_output_tokens": result[0].get("total_output_tokens", 0),
                }

            return {
                "total_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
            }
        except PyMongoError as e:
            logger.error(f"Failed to get usage summary: {e}")
            return {
                "total_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
            }

    async def get_top_users(
        self,
        *,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get top users by usage count.

        Args:
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Maximum number of users to return

        Returns:
            List of users with their usage statistics
        """
        query: Dict[str, Any] = {}
        if start_time or end_time:
            query["timestamp"] = {}
            if start_time:
                query["timestamp"]["$gte"] = start_time
            if end_time:
                query["timestamp"]["$lte"] = end_time

        try:
            pipeline: List[Dict[str, Any]] = [
                {"$match": query},
                {
                    "$group": {
                        "_id": "$user_id",
                        "total_requests": {"$sum": 1},
                        "total_input_tokens": {"$sum": "$input_tokens"},
                        "total_output_tokens": {"$sum": "$output_tokens"},
                    }
                },
                {"$sort": {"total_requests": -1}},
                {"$limit": limit},
            ]

            cursor = await self._collection.aggregate(pipeline)
            result = await cursor.to_list(length=limit)

            return [
                {
                    "user_id": doc["_id"],
                    "total_requests": doc["total_requests"],
                    "total_input_tokens": doc.get("total_input_tokens", 0),
                    "total_output_tokens": doc.get("total_output_tokens", 0),
                }
                for doc in result
            ]
        except PyMongoError as e:
            logger.error(f"Failed to get top users: {e}")
            return []
