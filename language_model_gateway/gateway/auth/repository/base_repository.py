import logging
from abc import abstractmethod, ABCMeta
from typing import Any, Dict, Optional, Type

from bson import ObjectId

from language_model_gateway.gateway.auth.models.base_db_model import BaseDbModel

logger = logging.getLogger(__name__)


class AsyncBaseRepository[T: BaseDbModel](metaclass=ABCMeta):
    """
    Async MongoDB repository for Pydantic models with comprehensive async support.
    """

    @abstractmethod
    async def insert(self, collection_name: str, model: T) -> ObjectId:
        """
        Save a Pydantic model to MongoDB collection asynchronously.

        Args:
            collection_name (str): Name of the collection
            model (T): Pydantic model to save

        Returns:
            ObjectId: Inserted document's ID
        """
        ...

    @abstractmethod
    async def find_by_id(
        self, collection_name: str, model_class: Type[T], document_id: ObjectId
    ) -> Optional[T]: ...

    @abstractmethod
    async def find_by_fields(
        self,
        collection_name: str,
        model_class: Type[T],
        fields: Dict[str, str],
    ) -> Optional[T]: ...

    @abstractmethod
    async def find_many(
        self,
        collection_name: str,
        model_class: Type[T],
        filter_dict: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[T]: ...

    @abstractmethod
    async def update_by_id(
        self,
        collection_name: str,
        document_id: ObjectId,
        update_data: T,
        model_class: Type[T],
    ) -> Optional[T]: ...

    @abstractmethod
    async def delete_by_id(
        self, collection_name: str, document_id: ObjectId
    ) -> bool: ...

    @abstractmethod
    async def insert_or_update(
        self,
        *,
        collection_name: str,
        model_class: Type[T],
        item: T,
        keys: Dict[str, str],
    ) -> ObjectId:
        """
        Insert a new item or update an existing one in the collection.

        Args:
            collection_name (str): Name of the collection
            model_class (Type[T]): Pydantic model class
            item (T): Pydantic model instance to insert or update
            keys (Dict[str, str]): Fields that uniquely identify the document
        Returns:
            ObjectId: The ID of the inserted or updated document
        """
        ...
