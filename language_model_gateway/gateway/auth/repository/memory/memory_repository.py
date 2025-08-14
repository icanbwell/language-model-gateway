from typing import Type, Dict, override, Any, Callable

from bson import ObjectId

from language_model_gateway.gateway.auth.models.base_db_model import BaseDbModel
from language_model_gateway.gateway.auth.repository.base_repository import (
    AsyncBaseRepository,
)


class AsyncMemoryRepository[T: BaseDbModel](AsyncBaseRepository[T]):
    """
    In-memory repository for Pydantic models with comprehensive async support.
    """

    def __init__(self) -> None:
        self._storage: dict[ObjectId, T] = {}

    @override
    async def insert(self, collection_name: str, model: T) -> ObjectId:
        self._storage[model.id] = model
        return model.id

    @override
    async def find_by_id(
        self, collection_name: str, model_class: type[T], document_id: ObjectId
    ) -> T | None:
        return self._storage.get(document_id)

    @override
    async def find_by_fields(
        self, collection_name: str, model_class: type[T], fields: dict[str, str | None]
    ) -> T | None:
        for item in self._storage.values():
            if all(getattr(item, k) == v for k, v in fields.items()):
                return item
        return None

    @override
    async def find_many(
        self,
        collection_name: str,
        model_class: type[T],
        filter_dict: dict[str, Any] | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[T]:
        items = list(self._storage.values())
        if filter_dict:
            items = [
                item
                for item in items
                if all(getattr(item, k) == v for k, v in filter_dict.items())
            ]
        return items[skip : skip + limit]

    @override
    async def update_by_id(
        self,
        collection_name: str,
        document_id: ObjectId,
        update_data: T,
        model_class: type[T],
    ) -> T | None:
        if document_id in self._storage:
            self._storage[document_id] = update_data
            return update_data
        return None

    @override
    async def delete_by_id(self, collection_name: str, document_id: ObjectId) -> bool:
        if document_id in self._storage:
            del self._storage[document_id]
            return True
        return False

    @override
    async def insert_or_update(
        self,
        *,
        collection_name: str,
        model_class: Type[T],
        item: T,
        keys: Dict[str, str | None],
        on_update: Callable[[T], T] = lambda x: x,
        on_insert: Callable[[T], T] = lambda x: x,
    ) -> ObjectId:
        """
        Insert or update a Pydantic model in the in-memory storage.
        If the model already exists, it will be updated; otherwise, it will be inserted.
        :param collection_name: Name of the collection (not used in memory storage).
        :param model_class: The Pydantic model class.
        :param item: The Pydantic model instance to insert or update.
        :param keys: Fields to match for updating an existing item.
        :param on_update: Function to apply on update (default is identity).
        :param on_insert: Function to apply on insert (default is identity).
        :return: The ID of the inserted or updated item.

        """
        if item.id in self._storage:
            item = on_update(item)
            # Update existing item
            self._storage[item.id] = item
        else:
            # Insert new item
            item = on_insert(item)
            self._storage[item.id] = item
        return item.id
